from analysis_fixtures import risk_request
from decision.service import evaluate
from factories import default_request, golden_snapshot


def test_unknown_risk_propagates_and_known_risk_uses_assigned_cohorts():
    unknown = evaluate(golden_snapshot(), default_request()).portfolio.risk
    assert unknown.rerun_gpu_hours is None
    assert unknown.additional_cpu_cost_usd is None
    known = evaluate(golden_snapshot(), risk_request(default_request())).portfolio.risk
    assert known.rerun_gpu_hours.point == 5
    assert known.rerun_reference_cost_usd.point == 12.5
    assert known.additional_cpu_core_hours.high == 60
    assert known.added_job_hours.point == 2
