import hashlib
import json
from pathlib import Path

from decision.contracts import Evaluation, EvidencePage
from factories import default_request, golden_snapshot

FIXTURES = Path(__file__).parents[1] / "contracts/fixtures"


def test_golden_inputs_are_hand_checked():
    assert golden_snapshot().jobs.gpu_hours.sum() == 46
    assert default_request().selected_action_ids == ["cpu_migration"]


def test_evaluation_fixture_totals():
    one = Evaluation.model_validate_json((FIXTURES / "evaluation.json").read_text())
    both = Evaluation.model_validate_json((FIXTURES / "evaluation-both-actions.json").read_text())
    assert one.portfolio.recoverable_gpu_hours.point == 15
    assert both.portfolio.recoverable_gpu_hours.point == 17
    assert sum(float(action.standalone_recoverable_gpu_hours.point) for action in both.actions) == 20
    for evaluation in (one, both):
        request = evaluation.request.model_dump(mode="json")
        request["selected_action_ids"] = sorted(request["selected_action_ids"], key=["cpu_migration", "idle_session_reclaim"].index)
        payload = json.dumps({"dataset_id": evaluation.meta.dataset_id, "analysis_version": "track2-decision-v1", "request": request}, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
        assert evaluation.meta.evaluation_id == hashlib.sha256(payload).hexdigest()


def test_evidence_fixture_scopes_and_contributions():
    cpu = EvidencePage.model_validate_json((FIXTURES / "evidence-cpu-default.json").read_text())
    idle = EvidencePage.model_validate_json((FIXTURES / "evidence-idle-standalone.json").read_text())
    assert sum(float(row.contribution_gpu_hours.point) for row in cpu.rows) == 15
    assert sum(float(row.contribution_gpu_hours.point) for row in idle.rows) == 5


def test_idle_evidence_preserves_measured_and_capped_hours():
    for name in ("evidence-idle.json", "evidence-idle-standalone.json"):
        rows = EvidencePage.model_validate_json((FIXTURES / name).read_text()).rows
        assert (rows[0].measured_gpu_hours, rows[0].capped_gpu_hours, rows[0].candidate_gpu_hours) == (20, 20, 12)
        assert (rows[1].measured_gpu_hours, rows[1].capped_gpu_hours, rows[1].candidate_gpu_hours) == (16, 16, 8)
