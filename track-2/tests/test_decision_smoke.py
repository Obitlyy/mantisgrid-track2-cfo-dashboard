import os
from pathlib import Path

import pytest

from decision.data import load_snapshot
from decision.service import evaluate, evidence_page
from factories import default_request


@pytest.mark.real_data
def test_real_data_decision_chain_is_recomputable():
    configured = os.environ.get("TRACK2_DATA_DIR")
    if not configured:
        pytest.skip("TRACK2_DATA_DIR is required for the explicit real-data smoke test")
    snapshot = load_snapshot(Path(configured))
    request = default_request().model_copy(update={"selected_action_ids": ["cpu_migration", "idle_session_reclaim"]})
    result = evaluate(snapshot, request)
    assert result.meta.dataset_id == snapshot.dataset_id
    assert sum(row.measured_gpu_hours for row in result.baseline.outcomes) == pytest.approx(result.baseline.measured_gpu_hours)
    assert result.portfolio.recoverable_gpu_hours.high <= sum(action.standalone_recoverable_gpu_hours.high for action in result.actions)
    for action in result.actions:
        page = evidence_page(snapshot, request, action.action_id, "marginal", 0, 1)
        assert page.meta.evaluation_id == result.meta.evaluation_id
