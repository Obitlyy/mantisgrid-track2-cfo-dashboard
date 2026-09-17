from decimal import Decimal, ROUND_HALF_UP
from decision.errors import DecisionError
def _export(e,digits):
    q=Decimal("1").scaleb(-digits); rnd=lambda x:float(Decimal(str(x)).quantize(q,rounding=ROUND_HALF_UP))
    return {"low":rnd(e.low),"point":rnd(e.point),"high":rnd(e.high),"interval_kind":e.interval_kind,"basis":e.basis}
def build_claims(evaluation,team):
    team=team.strip()
    if not team: raise DecisionError("INVALID_REQUEST","Team must not be blank.",{"field":"team"},422)
    return {"team":team,"recoverable_gpu_hours":_export(evaluation.portfolio.recoverable_gpu_hours,6),"recoverable_usd":_export(evaluation.portfolio.reference_savings_usd,2),"cancelled_is_waste":False,"cancelled_rationale":"CANCELLED jobs are not treated as waste; only explicit low-activity candidates enter scenarios.","cash_savings_claimed":False,"analysis_provenance":{"dataset_id":evaluation.meta.dataset_id,"evaluation_id":evaluation.meta.evaluation_id,"schema_version":evaluation.meta.schema_version,"analysis_version":evaluation.meta.analysis_version,"evaluation_request":evaluation.request.model_dump(mode="json"),"reference_currency":"USD","cash_savings_claimed":False}}
