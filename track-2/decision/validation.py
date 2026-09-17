"""Claims checks in addition to the unchanged official submission validator."""
from __future__ import annotations

import math

from decision.claims import build_claims
from decision.contracts import Evaluation


def validate_claims_semantics(claims: dict, evaluation: Evaluation) -> list[str]:
    problems: list[str] = []
    if not isinstance(claims, dict):
        return ["claims must be an object"]
    team = claims.get("team")
    if not isinstance(team, str) or not team.strip():
        return ["team must be nonblank"]
    expected = build_claims(evaluation, team)

    def compare(actual, wanted, path):
        if isinstance(wanted, dict):
            if not isinstance(actual, dict):
                problems.append(f"{path}: expected an object")
                return
            for key, value in wanted.items():
                if key not in actual:
                    problems.append(f"{path}.{key}: missing")
                else:
                    compare(actual[key], value, f"{path}.{key}")
            for key in actual.keys() - wanted.keys():
                problems.append(f"{path}.{key}: unsupported or uninvestigated claim")
        elif isinstance(wanted, (float, int)) and not isinstance(wanted, bool):
            if isinstance(actual, bool) or not isinstance(actual, (int, float)) or not math.isfinite(actual) or actual != wanted:
                problems.append(f"{path}: differs from recomputed rounded value")
        elif type(actual) is not type(wanted) or actual != wanted:
            problems.append(f"{path}: differs from current evaluation")

    # Human notes may be added without changing the scope or numerical claims.
    compare({k: v for k, v in claims.items() if k not in {"notes", "_comment"}}, expected, "claims")
    selected = set(evaluation.request.selected_action_ids)
    ceiling = min(evaluation.baseline.measured_gpu_hours,
                  sum(action.candidate_gpu_hours for action in evaluation.actions if action.action_id in selected))
    gpu = evaluation.portfolio.recoverable_gpu_hours
    usd = evaluation.portfolio.reference_savings_usd
    for name, estimate in (("recoverable_gpu_hours", gpu), ("recoverable_usd", usd)):
        values = [estimate.low, estimate.point, estimate.high]
        if not all(math.isfinite(x) for x in values) or not 0 <= values[0] <= values[1] <= values[2]:
            problems.append(f"{name}: internal bounds must be finite, nonnegative and ordered")
        if estimate.interval_kind != "scenario" or estimate.confidence is not None or not estimate.basis.strip():
            problems.append(f"{name}: must describe a scenario, without calibrated confidence")
    if gpu.high > ceiling + 1e-6:
        problems.append("recoverable_gpu_hours: exceeds selected candidate or measured sample ceiling")
    price = evaluation.request.pricing.usd_per_gpu_hour
    for bound in ("low", "point", "high"):
        if not math.isclose(getattr(usd, bound), getattr(gpu, bound) * price, rel_tol=0, abs_tol=1e-6):
            problems.append(f"recoverable_usd.{bound}: inconsistent reference price")
    return problems
