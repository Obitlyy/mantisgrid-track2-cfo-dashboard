import importlib
import json
import math

import pytest

from decision.claims import build_claims
from decision.service import evaluate
from factories import default_request, golden_snapshot


def validate(claims, evaluation):
    return importlib.import_module("decision.validation").validate_claims_semantics(claims, evaluation)


def test_current_claims_pass_with_unknown_costs_omitted():
    evaluation = evaluate(golden_snapshot(), default_request())
    claims = build_claims(evaluation, "Fixture Team")
    assert claims["recoverable_gpu_hours"]["point"] == 15
    assert claims["recoverable_usd"]["point"] == 37.5
    assert validate(claims, evaluation) == []


@pytest.mark.parametrize("field,value", [("point", 16), ("low", -1), ("high", math.inf), ("point", True), ("confidence", None), ("interval_kind", "uncertainty"), ("basis", "")])
def test_rejects_detached_or_fabricated_estimate(field, value):
    evaluation = evaluate(golden_snapshot(), default_request())
    claims = build_claims(evaluation, "Fixture Team")
    claims["recoverable_gpu_hours"][field] = value
    assert any("recoverable_gpu_hours" in p for p in validate(claims, evaluation))


@pytest.mark.parametrize("field,value", [("dataset_id", "stale"), ("evaluation_id", "stale"), ("cash_savings_claimed", True), ("evaluation_request", {})])
def test_rejects_stale_or_modified_provenance(field, value):
    evaluation = evaluate(golden_snapshot(), default_request())
    claims = build_claims(evaluation, "Fixture Team")
    claims["analysis_provenance"][field] = value
    assert validate(claims, evaluation)


@pytest.mark.parametrize("field,value", [("incident_confidence", .8), ("node_triage", []), ("hardware_attributable_failures", 0), ("cash_savings_usd", 0), ("additional_cpu_cost_usd", 0), ("cash_savings_claimed", True)])
def test_rejects_uninvestigated_and_unknown_claims(field, value):
    evaluation = evaluate(golden_snapshot(), default_request())
    claims = build_claims(evaluation, "Fixture Team")
    claims[field] = value
    assert validate(claims, evaluation)


def test_semantics_checks_internal_candidate_ceiling_even_when_export_matches():
    evaluation = evaluate(golden_snapshot(), default_request())
    evaluation.portfolio.recoverable_gpu_hours.high = 100
    assert validate(build_claims(evaluation, "Fixture Team"), evaluation)


def test_rounding_does_not_reject_valid_fractional_ceiling():
    snapshot = golden_snapshot()
    snapshot.gpus.loc[0, "totalexecutiontime_sec"] -= .000001
    evaluation = evaluate(snapshot, default_request())
    assert validate(build_claims(evaluation, "Fixture Team"), evaluation) == []
