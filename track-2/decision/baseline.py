import numpy as np
import pandas as pd

from decision.contracts import Baseline, OutcomeRow
from decision.errors import DecisionError

OUTCOMES = ["COMPLETED", "CANCELLED", "FAILED", "TIMEOUT", "NODE_FAIL", "UNDECODED_11", "UNDECODED_1024"]


def compute_baseline(snapshot, pricing):
    jobs = snapshot.jobs
    hours = pd.to_numeric(jobs.get("gpu_hours"), errors="coerce")
    util = pd.to_numeric(jobs.get("sm_util_avg"), errors="coerce")
    if len(jobs) and (hours.isna().any() or not np.isfinite(hours).all()):
        raise DecisionError("DATA_INVALID", "Invalid measured GPU-hours.", {"field": "gpu_hours", "invalid_jobs": int((~np.isfinite(hours)).sum())}, 503)
    if len(jobs) and (util.isna().any() or not np.isfinite(util).all()):
        raise DecisionError("DATA_INVALID", "Missing baseline SM utilization.", {"field": "sm_util_avg", "invalid_jobs": int((~np.isfinite(util)).sum())}, 503)
    total = float(hours.sum()) if len(jobs) else 0.0
    if len(jobs) and total <= 0:
        raise DecisionError("DATA_INVALID", "Non-positive measured GPU-hours.", {"field": "gpu_hours", "jobs": len(jobs)}, 503)
    states = jobs.get("state_name", pd.Series(index=jobs.index, dtype=object)).fillna("UNKNOWN").astype(str)
    known = set(OUTCOMES)
    states = states.where(states.isin(known), "UNKNOWN")
    ordered = OUTCOMES + sorted(set(states) - known)
    rows = []
    for state in ordered:
        mask = states == state
        value = float(hours[mask].sum())
        rows.append(OutcomeRow(state_name=state, jobs=int(mask.sum()), measured_gpu_hours=value,
                               share_of_measured_gpu_hours=value / total if total else 0.0,
                               reference_cost_usd=value * float(pricing.usd_per_gpu_hour)))
    weighted = hours * util.clip(0, 100) / 100 if len(jobs) else hours
    completed = states == "COMPLETED"
    caveats = ["Historical measured GPU-hours include all terminal outcomes and are not an intervention estimate."]
    if not len(jobs): caveats.append("Empty sample: shares are reported as zero.")
    if (states == "UNKNOWN").any(): caveats.append("Blank or unmatched terminal states are reported as UNKNOWN.")
    return Baseline(jobs=len(jobs), gpu_rows=len(snapshot.gpus), measured_gpu_hours=total,
                    computed_proxy_gpu_hours=float(weighted.sum()),
                    completed_computed_proxy_gpu_hours=float(weighted[completed].sum()),
                    non_completed_compute_share=(1 - float(weighted[completed].sum()) / total) if total else 0.0,
                    reference_cost_usd=total * float(pricing.usd_per_gpu_hour), outcomes=rows, caveats=caveats)
