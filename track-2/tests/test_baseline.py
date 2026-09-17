import math
import pytest

from analysis_fixtures import clone_snapshot
from decision.baseline import compute_baseline
from decision.errors import DecisionError
from factories import default_request, golden_snapshot


def test_baseline_uses_full_measured_sample():
    result = compute_baseline(golden_snapshot(), default_request().pricing)
    assert (result.jobs, result.gpu_rows, result.measured_gpu_hours) == (3, 5, 46)
    assert result.computed_proxy_gpu_hours == pytest.approx(.32)
    assert result.completed_computed_proxy_gpu_hours == 0
    assert result.non_completed_compute_share == 1
    assert result.reference_cost_usd == 115
    assert sum(row.measured_gpu_hours for row in result.outcomes) == 46


def test_baseline_rejects_nonfinite_measured_hours():
    snapshot = golden_snapshot()
    jobs = snapshot.jobs.copy()
    jobs.loc[0, "gpu_hours"] = math.nan
    with pytest.raises(DecisionError, match="measured") as error:
        compute_baseline(clone_snapshot(snapshot, jobs=jobs), default_request().pricing)
    assert error.value.code == "DATA_INVALID"


def test_unknown_terminal_states_preserve_hours_in_one_unknown_bucket():
    snapshot = golden_snapshot()
    jobs = snapshot.jobs.copy()
    jobs["state_name"] = ["OTHER", "", None]
    result = compute_baseline(clone_snapshot(snapshot, jobs=jobs), default_request().pricing)
    unknown = [row for row in result.outcomes if row.state_name == "UNKNOWN"]
    assert len(unknown) == 1
    assert (unknown[0].jobs, unknown[0].measured_gpu_hours) == (3, 46)
    assert len(result.outcomes) == 8
