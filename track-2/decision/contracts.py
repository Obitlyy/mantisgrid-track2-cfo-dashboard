from __future__ import annotations

import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, field_validator, model_validator

ActionId = Literal["cpu_migration", "idle_session_reclaim"]
Origin = Literal["real_telemetry", "synthetic_incident", "test_fixture"]
Unit = Literal["gpu_hours", "usd", "cpu_core_hours", "job_hours"]
Number = Annotated[StrictFloat | StrictInt, Field()]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Bounds(ContractModel):
    low: Number
    point: Number
    high: Number

    @model_validator(mode="after")
    def ordered(self):
        values = (float(self.low), float(self.point), float(self.high))
        if not all(math.isfinite(v) for v in values) or not (0 <= values[0] <= values[1] <= values[2]):
            raise ValueError("bounds must be finite and satisfy 0 <= low <= point <= high")
        return self


class Estimate(Bounds):
    unit: Unit
    interval_kind: Literal["scenario"] = "scenario"
    confidence: None = None
    basis: str


class Pricing(ContractModel):
    usd_per_gpu_hour: Number = Field(ge=0, le=1_000_000)
    usd_per_cpu_core_hour: Number | None = Field(default=None, ge=0, le=1_000_000)


class CpuMigrationParameters(ContractModel):
    recoverable_fraction: Bounds
    additional_cpu_core_hours_per_gpu_hour: Bounds | None
    rerun_gpu_hours_per_candidate_gpu_hour: Bounds | None
    added_elapsed_hours_per_job: Bounds | None


class IdleSessionParameters(ContractModel):
    recoverable_fraction: Bounds
    rerun_gpu_hours_per_candidate_gpu_hour: Bounds | None
    added_elapsed_hours_per_job: Bounds | None


def _check_max(value: Bounds | None, maximum: float, label: str) -> None:
    if value is not None and float(value.high) > maximum:
        raise ValueError(f"{label}.high must be <= {maximum}")


class EvaluationRequest(ContractModel):
    selected_action_ids: list[ActionId]
    pricing: Pricing
    cpu_migration: CpuMigrationParameters
    idle_session_reclaim: IdleSessionParameters

    @model_validator(mode="after")
    def validate_ranges(self):
        if len(self.selected_action_ids) != len(set(self.selected_action_ids)):
            raise ValueError("selected_action_ids must not contain duplicates")
        _check_max(self.cpu_migration.recoverable_fraction, 1, "recoverable_fraction")
        _check_max(self.idle_session_reclaim.recoverable_fraction, 1, "recoverable_fraction")
        _check_max(self.cpu_migration.rerun_gpu_hours_per_candidate_gpu_hour, 1, "rerun")
        _check_max(self.idle_session_reclaim.rerun_gpu_hours_per_candidate_gpu_hour, 1, "rerun")
        _check_max(self.cpu_migration.additional_cpu_core_hours_per_gpu_hour, 1_000_000, "additional_cpu")
        _check_max(self.cpu_migration.added_elapsed_hours_per_job, 1_000_000, "added_elapsed")
        _check_max(self.idle_session_reclaim.added_elapsed_hours_per_job, 1_000_000, "added_elapsed")
        return self


class SampleWindow(ContractModel):
    start_offset_sec: Number
    end_offset_sec: Number
    epoch_offset_sec: int
    mapped_start_utc: str
    mapped_end_utc: str
    calendar_is_mapped: Literal[True] = True


class Meta(ContractModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    analysis_version: Literal["track2-decision-v1"] = "track2-decision-v1"
    dataset_id: str
    evaluation_id: str | None
    data_origin: Literal["official_dataset", "test_fixture"]
    sample_window: SampleWindow


class OutcomeRow(ContractModel):
    state_name: str; jobs: int; measured_gpu_hours: Number; share_of_measured_gpu_hours: Number; reference_cost_usd: Number
class Baseline(ContractModel):
    jobs: int; gpu_rows: int; measured_gpu_hours: Number; computed_proxy_gpu_hours: Number; completed_computed_proxy_gpu_hours: Number; non_completed_compute_share: Number; reference_cost_usd: Number; outcomes: list[OutcomeRow]; caveats: list[str]
class ExclusionCount(ContractModel):
    reason: str; jobs: int
class RiskResult(ContractModel):
    rerun_gpu_hours: Estimate | None; rerun_reference_cost_usd: Estimate | None; additional_cpu_core_hours: Estimate | None; additional_cpu_cost_usd: Estimate | None; added_job_hours: Estimate | None; cash_savings_usd: None = None; unknowns: list[str]
class Pilot(ContractModel):
    success_metrics: list[str]; stop_conditions: list[str]; rollback_steps: list[str]
class ActionEvaluation(ContractModel):
    action_id: ActionId; title: str; owner_role: str; action: str; effort: Literal["low", "medium", "high"]; rank: int; evidence_origin: Literal["real_telemetry", "test_fixture"]; candidate_jobs: int; candidate_gpu_hours: Number; excluded_jobs: int; exclusion_counts: list[ExclusionCount]; finding_count: int; standalone_recoverable_gpu_hours: Estimate; standalone_reference_savings_usd: Estimate; marginal_recoverable_gpu_hours: Estimate | None; marginal_reference_savings_usd: Estimate | None; standalone_risk: RiskResult; marginal_risk: RiskResult | None; pilot: Pilot; warnings: list[str]
class Portfolio(ContractModel):
    selected_action_ids: list[ActionId]; allocation_order: list[ActionId]; unique_jobs: int; overlap_jobs: int; recoverable_gpu_hours: Estimate; reference_savings_usd: Estimate; risk: RiskResult; sample_capacity_target_fraction: Number; sample_capacity_target_gpu_hours: Number; sample_capacity_gap_gpu_hours: Estimate; caveats: list[str]
class Evaluation(ContractModel):
    meta: Meta; request: EvaluationRequest; price_book_version: str; baseline: Baseline; actions: list[ActionEvaluation]; portfolio: Portfolio; ranking_basis: str; audit_status: Literal["not_run", "running", "completed", "partial", "failed"]; warnings: list[str]
class DecisionConfig(ContractModel):
    meta: Meta; default_request: EvaluationRequest; action_ids: list[ActionId]; allocation_order: list[ActionId]
class JobEvidenceRow(ContractModel):
    job_id: str; user_id: str | None; state_name: str; gpu_count: int; measured_gpu_hours: Number; capped_gpu_hours: Number | None; candidate_gpu_hours: Number | None; contribution_gpu_hours: Estimate; eligibility: Literal["included", "excluded", "overlap_assigned_elsewhere"]; reasons: list[str]; finding_ids: list[str]; nodes: list[str]
class EvidencePage(ContractModel):
    meta: Meta; action_id: ActionId; scope: Literal["standalone", "marginal"]; rows: list[JobEvidenceRow]; total: int; offset: int; limit: int; next_offset: int | None
class GpuDetail(ContractModel):
    node: str; gpu_id: int; totalexecutiontime_sec: Number | None; smutilization_pct_avg: Number | None; smutilization_pct_max: Number | None; measured_gpu_hours: Number | None; capped_gpu_hours: Number | None; quality_flags: list[str]
class JobDetail(ContractModel):
    meta: Meta; job_id: str; user_id: str | None; array_job_id: str | None; state_name: str; job_type: str | None; attempts: int; hit_node_failure: bool; nodefail_nodes: list[str]; nodefail_exact: bool; time_submit_offset_sec: Number | None; time_start_offset_sec: Number | None; time_end_offset_sec: Number | None; walltime_sec: Number | None; measured_gpu_hours: Number; sm_util_avg: Number | None; sm_util_max: Number | None; finding_ids: list[str]; gpus: list[GpuDetail]; quality_flags: list[str]
class FindingDetail(ContractModel):
    meta: Meta; finding_id: str; detector_id: str; title: str; description: str; resource_ids: list[str]; root_cause_ids: list[str]; job_ids: list[str]; node_names: list[str]; evidence_origin: Origin; impact_scope: str | None; impact_kind: str | None; reported_impact_gpu_hours: Number | None; causal_status: Literal["available", "no_chain"]; method: str
class ToolCallRecord(ContractModel):
    call_id: str; sequence: int; tool_name: str; arguments: dict; started_at_utc: str; duration_ms: int; status: Literal["success", "error", "timeout"]; result: dict | None; error: str | None
class NodeAudit(ContractModel):
    node_name: str; resource_id: str; cause: Literal["hardware", "user_code", "workload_mix", "cannot_determine"]; verdict: Literal["inspect", "no_drain", "cannot_determine"]; scope_description: str; finding_ids: list[str]; reported_findings: int; returned_findings: int; truncated: bool; reasoning: str
class Investigation(ContractModel):
    investigation_id: Literal["node_recommendation_audit"]; dataset_id: str; status: Literal["not_run", "running", "completed", "partial", "failed"]; verdict: Literal["accept", "revise", "reject", "cannot_determine"]; evidence_origin: Literal["real_telemetry", "synthetic_incident", "mixed"]; recommendation_id: str; finding_ids: list[str]; summary: str; limitations: list[str]; nodes: list[NodeAudit]; nominal_drain_gpu_hours_24h: Number; tool_calls: list[ToolCallRecord]; model_used: str | None; token_usage: dict[str, int] | None
class InvestigationResponse(ContractModel):
    meta: Meta; investigation: Investigation
class DecisionHealth(ContractModel):
    status: Literal["ready", "not_ready"]; schema_version: Literal["1.0.0"] = "1.0.0"; dataset_id: str | None; audit_status: Literal["not_run", "running", "completed", "partial", "failed"]
class ClaimsRequest(ContractModel):
    team: str; evaluation_request: EvaluationRequest
    @field_validator("team")
    @classmethod
    def team_not_blank(cls, value: str):
        if not value.strip(): raise ValueError("team must not be blank")
        return value
class ClaimsResponse(ContractModel):
    meta: Meta; claims: dict
class ErrorInfo(ContractModel):
    code: str; message: str; details: dict
class ErrorResponse(ContractModel):
    error: ErrorInfo; schema_version: Literal["1.0.0"] = "1.0.0"

NETWORK_MODELS = [Bounds, Estimate, Pricing, CpuMigrationParameters, IdleSessionParameters, EvaluationRequest, SampleWindow, Meta, OutcomeRow, Baseline, ExclusionCount, RiskResult, Pilot, ActionEvaluation, Portfolio, Evaluation, DecisionConfig, JobEvidenceRow, EvidencePage, GpuDetail, JobDetail, FindingDetail, ToolCallRecord, NodeAudit, Investigation, InvestigationResponse, DecisionHealth, ClaimsRequest, ClaimsResponse, ErrorInfo, ErrorResponse]
