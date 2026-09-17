from decision.claims import build_claims
from decision.service import evaluate
from factories import default_request, golden_snapshot


def test_claims_are_derived_from_evaluation():
    evaluation = evaluate(golden_snapshot(), default_request())
    claims = build_claims(evaluation, " Team ")
    assert claims["team"] == "Team"
    assert claims["recoverable_gpu_hours"]["point"] == 15
    assert claims["recoverable_usd"]["point"] == 37.5
    assert claims["analysis_provenance"]["evaluation_id"] == evaluation.meta.evaluation_id
    assert claims["cash_savings_claimed"] is False
