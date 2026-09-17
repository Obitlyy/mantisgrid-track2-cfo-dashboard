from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from decision.bootstrap import EvaluationCache, latest_investigation, snapshot_from_app
from decision.claims import build_claims
from decision.contracts import (
    ClaimsRequest,
    ClaimsResponse,
    DecisionConfig,
    DecisionHealth,
    ErrorInfo,
    ErrorResponse,
    Evaluation,
    EvaluationRequest,
    EvidencePage,
    FindingDetail,
    InvestigationResponse,
    JobDetail,
    Meta,
)
from decision.errors import DecisionError
from decision.service import (
    _eid as evaluation_identity,
    evaluate as run_evaluate,
    evidence_page,
    finding_detail,
    job_detail,
)


def _error(code: str, message: str, details: dict, status: int) -> JSONResponse:
    body = ErrorResponse(error=ErrorInfo(code=code, message=message, details=details))
    return JSONResponse(status_code=status, content=body.model_dump(mode="json"))


class DecisionRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handler(request: Request):
            try:
                return await original(request)
            except RequestValidationError as exc:
                invalid = [
                    ".".join(map(str, item.get("loc", ()))) for item in exc.errors()
                ]
                return _error(
                    "INVALID_REQUEST",
                    "Request validation failed.",
                    {"invalid_fields": invalid},
                    422,
                )
            except DecisionError as exc:
                return _error(exc.code, exc.message, exc.details, exc.http_status)
            except Exception:
                return _error(
                    "INTERNAL_ERROR", "Internal decision service error.", {}, 500
                )

        return handler


router = APIRouter(route_class=DecisionRoute)


def get_snapshot(request: Request):
    return snapshot_from_app(request.app)


def _check(snapshot, dataset_id: str) -> None:
    if dataset_id != snapshot.dataset_id:
        raise DecisionError(
            "DATASET_MISMATCH",
            "Requested dataset does not match the loaded dataset.",
            {"requested": dataset_id, "current": snapshot.dataset_id},
            409,
        )


def _meta(snapshot) -> Meta:
    return Meta(
        dataset_id=snapshot.dataset_id,
        evaluation_id=None,
        data_origin=snapshot.data_origin,
        sample_window=snapshot.sample_window,
    )


def _audit(request: Request, snapshot):
    return latest_investigation(request.app, snapshot)


def _evaluation_key(snapshot, payload: EvaluationRequest) -> str:
    return evaluation_identity(snapshot, payload)


def _evaluate(request: Request, snapshot, payload: EvaluationRequest) -> Evaluation:
    cache = getattr(request.app.state, "decision_evaluation_cache", None)
    if cache is None:
        cache = EvaluationCache(maxsize=64)
        request.app.state.decision_evaluation_cache = cache
    result = cache.get_or_create(
        _evaluation_key(snapshot, payload), lambda: run_evaluate(snapshot, payload)
    )
    return result.model_copy(update={"audit_status": _audit(request, snapshot).status})


@router.get(
    "/health", response_model=DecisionHealth, responses={503: {"model": DecisionHealth}}
)
def health(request: Request):
    snapshot = getattr(request.app.state, "decision_snapshot", None)
    if snapshot is None:
        body = DecisionHealth(
            status="not_ready", dataset_id=None, audit_status="not_run"
        )
        return JSONResponse(status_code=503, content=body.model_dump(mode="json"))
    return DecisionHealth(
        status="ready",
        dataset_id=snapshot.dataset_id,
        audit_status=_audit(request, snapshot).status,
    )


@router.get(
    "/config", response_model=DecisionConfig, responses={503: {"model": ErrorResponse}}
)
def config(snapshot=Depends(get_snapshot)):
    fixture = Path(__file__).parents[1] / "contracts/fixtures/default-request.json"
    payload = EvaluationRequest.model_validate_json(fixture.read_text())
    return DecisionConfig(
        meta=_meta(snapshot),
        default_request=payload,
        action_ids=["cpu_migration", "idle_session_reclaim"],
        allocation_order=["cpu_migration", "idle_session_reclaim"],
    )


@router.post(
    "/evaluate",
    response_model=Evaluation,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def evaluate(payload: EvaluationRequest, request: Request, snapshot=Depends(get_snapshot)):
    return _evaluate(request, snapshot, payload)


@router.post(
    "/actions/{action_id}/evidence",
    response_model=EvidencePage,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def evidence(
    action_id: str,
    payload: EvaluationRequest,
    request: Request,
    scope: str = "standalone",
    offset: int = 0,
    limit: int = Query(50, ge=1, le=200),
    snapshot=Depends(get_snapshot),
):
    if offset < 0:
        raise DecisionError(
            "INVALID_REQUEST",
            "Evidence offset must be nonnegative.",
            {"offset": offset},
            422,
        )
    return evidence_page(snapshot, payload, action_id, scope, offset, limit)


@router.get(
    "/jobs/{job_id}", response_model=JobDetail, responses={503: {"model": ErrorResponse}}
)
def job(job_id: str, dataset_id: str, snapshot=Depends(get_snapshot)):
    _check(snapshot, dataset_id)
    return job_detail(snapshot, job_id)


@router.get(
    "/findings/{finding_id}",
    response_model=FindingDetail,
    responses={503: {"model": ErrorResponse}},
)
def finding(finding_id: str, dataset_id: str, snapshot=Depends(get_snapshot)):
    _check(snapshot, dataset_id)
    return finding_detail(snapshot, finding_id)


@router.get(
    "/investigations/node_recommendation_audit",
    response_model=InvestigationResponse,
    responses={503: {"model": ErrorResponse}},
)
def investigation(
    request: Request, dataset_id: str, snapshot=Depends(get_snapshot)
):
    _check(snapshot, dataset_id)
    return InvestigationResponse(
        meta=_meta(snapshot), investigation=_audit(request, snapshot)
    )


@router.post(
    "/claims",
    response_model=ClaimsResponse,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def claims(payload: ClaimsRequest, request: Request, snapshot=Depends(get_snapshot)):
    result = _evaluate(request, snapshot, payload.evaluation_request)
    return ClaimsResponse(meta=result.meta, claims=build_claims(result, payload.team))
