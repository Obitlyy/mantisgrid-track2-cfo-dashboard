// Generated from decision.schema.json. Do not edit.

export type Action = string;
export type ActionId = "cpu_migration" | "idle_session_reclaim";
export type CandidateGpuHours = number;
export type CandidateJobs = number;
export type Effort = "low" | "medium" | "high";
export type EvidenceOrigin = "real_telemetry" | "test_fixture";
export type ExcludedJobs = number;
export type Jobs = number;
export type Reason = string;
export type ExclusionCounts = ExclusionCount[];
export type FindingCount = number;
export type Basis = string;
export type Confidence = null;
export type High = number;
export type IntervalKind = "scenario";
export type Low = number;
export type Point = number;
export type Unit = "gpu_hours" | "usd" | "cpu_core_hours" | "job_hours";
export type CashSavingsUsd = null;
export type Unknowns = string[];
export type OwnerRole = string;
export type RollbackSteps = string[];
export type StopConditions = string[];
export type SuccessMetrics = string[];
export type Rank = number;
export type Title = string;
export type Warnings = string[];
export type Caveats = string[];
export type CompletedComputedProxyGpuHours = number;
export type ComputedProxyGpuHours = number;
export type GpuRows = number;
export type Jobs1 = number;
export type MeasuredGpuHours = number;
export type NonCompletedComputeShare = number;
export type Jobs2 = number;
export type MeasuredGpuHours1 = number;
export type ReferenceCostUsd = number;
export type ShareOfMeasuredGpuHours = number;
export type StateName = string;
export type Outcomes = OutcomeRow[];
export type ReferenceCostUsd1 = number;
export type High1 = number;
export type Low1 = number;
export type Point1 = number;
export type UsdPerCpuCoreHour = number | null;
export type UsdPerGpuHour = number;
export type SelectedActionIds = ("cpu_migration" | "idle_session_reclaim")[];
export type Team = string;
export type AnalysisVersion = "track2-decision-v1";
export type DataOrigin = "official_dataset" | "test_fixture";
export type DatasetId = string;
export type EvaluationId = string | null;
export type CalendarIsMapped = true;
export type EndOffsetSec = number;
export type EpochOffsetSec = number;
export type MappedEndUtc = string;
export type MappedStartUtc = string;
export type StartOffsetSec = number;
export type SchemaVersion = "1.0.0";
export type ActionIds = ("cpu_migration" | "idle_session_reclaim")[];
export type AllocationOrder = ("cpu_migration" | "idle_session_reclaim")[];
export type AuditStatus = "not_run" | "running" | "completed" | "partial" | "failed";
export type DatasetId1 = string | null;
export type SchemaVersion1 = "1.0.0";
export type Status = "ready" | "not_ready";
export type Code = string;
export type Message = string;
export type SchemaVersion2 = "1.0.0";
export type Actions = ActionEvaluation[];
export type AuditStatus1 = "not_run" | "running" | "completed" | "partial" | "failed";
export type AllocationOrder1 = ("cpu_migration" | "idle_session_reclaim")[];
export type Caveats1 = string[];
export type OverlapJobs = number;
export type SampleCapacityTargetFraction = number;
export type SampleCapacityTargetGpuHours = number;
export type SelectedActionIds1 = ("cpu_migration" | "idle_session_reclaim")[];
export type UniqueJobs = number;
export type PriceBookVersion = string;
export type RankingBasis = string;
export type Warnings1 = string[];
export type ActionId1 = "cpu_migration" | "idle_session_reclaim";
export type Limit = number;
export type NextOffset = number | null;
export type Offset = number;
export type CandidateGpuHours1 = number | null;
export type CappedGpuHours = number | null;
export type Eligibility = "included" | "excluded" | "overlap_assigned_elsewhere";
export type FindingIds = string[];
export type GpuCount = number;
export type JobId = string;
export type MeasuredGpuHours2 = number;
export type Nodes = string[];
export type Reasons = string[];
export type StateName1 = string;
export type UserId = string | null;
export type Rows = JobEvidenceRow[];
export type Scope = "standalone" | "marginal";
export type Total = number;
export type CausalStatus = "available" | "no_chain";
export type Description = string;
export type DetectorId = string;
export type EvidenceOrigin1 = "real_telemetry" | "synthetic_incident" | "test_fixture";
export type FindingId = string;
export type ImpactKind = string | null;
export type ImpactScope = string | null;
export type JobIds = string[];
export type Method = string;
export type NodeNames = string[];
export type ReportedImpactGpuHours = number | null;
export type ResourceIds = string[];
export type RootCauseIds = string[];
export type Title1 = string;
export type CappedGpuHours1 = number | null;
export type GpuId = number;
export type MeasuredGpuHours3 = number | null;
export type Node = string;
export type QualityFlags = string[];
export type SmutilizationPctAvg = number | null;
export type SmutilizationPctMax = number | null;
export type TotalexecutiontimeSec = number | null;
export type DatasetId2 = string;
export type EvidenceOrigin2 = "real_telemetry" | "synthetic_incident" | "mixed";
export type FindingIds1 = string[];
export type InvestigationId = "node_recommendation_audit";
export type Limitations = string[];
export type ModelUsed = string | null;
export type Cause = "hardware" | "user_code" | "workload_mix" | "cannot_determine";
export type FindingIds2 = string[];
export type NodeName = string;
export type Reasoning = string;
export type ReportedFindings = number;
export type ResourceId = string;
export type ReturnedFindings = number;
export type ScopeDescription = string;
export type Truncated = boolean;
export type Verdict = "inspect" | "no_drain" | "cannot_determine";
export type Nodes1 = NodeAudit[];
export type NominalDrainGpuHours24H = number;
export type RecommendationId = string;
export type Status1 = "not_run" | "running" | "completed" | "partial" | "failed";
export type Summary = string;
export type TokenUsage = {
  [k: string]: number;
} | null;
export type CallId = string;
export type DurationMs = number;
export type Error = string | null;
export type Result = {
  [k: string]: unknown;
} | null;
export type Sequence = number;
export type StartedAtUtc = string;
export type Status2 = "success" | "error" | "timeout";
export type ToolName = string;
export type ToolCalls = ToolCallRecord[];
export type Verdict1 = "accept" | "revise" | "reject" | "cannot_determine";
export type ArrayJobId = string | null;
export type Attempts = number;
export type FindingIds3 = string[];
export type Gpus = GpuDetail[];
export type HitNodeFailure = boolean;
export type JobId1 = string;
export type JobType = string | null;
export type MeasuredGpuHours4 = number;
export type NodefailExact = boolean;
export type NodefailNodes = string[];
export type QualityFlags1 = string[];
export type SmUtilAvg = number | null;
export type SmUtilMax = number | null;
export type StateName2 = string;
export type TimeEndOffsetSec = number | null;
export type TimeStartOffsetSec = number | null;
export type TimeSubmitOffsetSec = number | null;
export type UserId1 = string | null;
export type WalltimeSec = number | null;

export interface Track2DecisionContracts {
  [k: string]: unknown;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "ActionEvaluation".
 */
export interface ActionEvaluation {
  action: Action;
  action_id: ActionId;
  candidate_gpu_hours: CandidateGpuHours;
  candidate_jobs: CandidateJobs;
  effort: Effort;
  evidence_origin: EvidenceOrigin;
  excluded_jobs: ExcludedJobs;
  exclusion_counts: ExclusionCounts;
  finding_count: FindingCount;
  marginal_recoverable_gpu_hours: Estimate | null;
  marginal_reference_savings_usd: Estimate | null;
  marginal_risk: RiskResult | null;
  owner_role: OwnerRole;
  pilot: Pilot;
  rank: Rank;
  standalone_recoverable_gpu_hours: Estimate;
  standalone_reference_savings_usd: Estimate;
  standalone_risk: RiskResult;
  title: Title;
  warnings: Warnings;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "ExclusionCount".
 */
export interface ExclusionCount {
  jobs: Jobs;
  reason: Reason;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "Estimate".
 */
export interface Estimate {
  basis: Basis;
  confidence?: Confidence;
  high: High;
  interval_kind?: IntervalKind;
  low: Low;
  point: Point;
  unit: Unit;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "RiskResult".
 */
export interface RiskResult {
  added_job_hours: Estimate | null;
  additional_cpu_core_hours: Estimate | null;
  additional_cpu_cost_usd: Estimate | null;
  cash_savings_usd?: CashSavingsUsd;
  rerun_gpu_hours: Estimate | null;
  rerun_reference_cost_usd: Estimate | null;
  unknowns: Unknowns;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "Pilot".
 */
export interface Pilot {
  rollback_steps: RollbackSteps;
  stop_conditions: StopConditions;
  success_metrics: SuccessMetrics;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "Baseline".
 */
export interface Baseline {
  caveats: Caveats;
  completed_computed_proxy_gpu_hours: CompletedComputedProxyGpuHours;
  computed_proxy_gpu_hours: ComputedProxyGpuHours;
  gpu_rows: GpuRows;
  jobs: Jobs1;
  measured_gpu_hours: MeasuredGpuHours;
  non_completed_compute_share: NonCompletedComputeShare;
  outcomes: Outcomes;
  reference_cost_usd: ReferenceCostUsd1;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "OutcomeRow".
 */
export interface OutcomeRow {
  jobs: Jobs2;
  measured_gpu_hours: MeasuredGpuHours1;
  reference_cost_usd: ReferenceCostUsd;
  share_of_measured_gpu_hours: ShareOfMeasuredGpuHours;
  state_name: StateName;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "Bounds".
 */
export interface Bounds {
  high: High1;
  low: Low1;
  point: Point1;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "ClaimsRequest".
 */
export interface ClaimsRequest {
  evaluation_request: EvaluationRequest;
  team: Team;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "EvaluationRequest".
 */
export interface EvaluationRequest {
  cpu_migration: CpuMigrationParameters;
  idle_session_reclaim: IdleSessionParameters;
  pricing: Pricing;
  selected_action_ids: SelectedActionIds;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "CpuMigrationParameters".
 */
export interface CpuMigrationParameters {
  added_elapsed_hours_per_job: Bounds | null;
  additional_cpu_core_hours_per_gpu_hour: Bounds | null;
  recoverable_fraction: Bounds;
  rerun_gpu_hours_per_candidate_gpu_hour: Bounds | null;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "IdleSessionParameters".
 */
export interface IdleSessionParameters {
  added_elapsed_hours_per_job: Bounds | null;
  recoverable_fraction: Bounds;
  rerun_gpu_hours_per_candidate_gpu_hour: Bounds | null;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "Pricing".
 */
export interface Pricing {
  usd_per_cpu_core_hour?: UsdPerCpuCoreHour;
  usd_per_gpu_hour: UsdPerGpuHour;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "ClaimsResponse".
 */
export interface ClaimsResponse {
  claims: Claims;
  meta: Meta;
}
export interface Claims {
  [k: string]: unknown;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "Meta".
 */
export interface Meta {
  analysis_version?: AnalysisVersion;
  data_origin: DataOrigin;
  dataset_id: DatasetId;
  evaluation_id: EvaluationId;
  sample_window: SampleWindow;
  schema_version?: SchemaVersion;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "SampleWindow".
 */
export interface SampleWindow {
  calendar_is_mapped?: CalendarIsMapped;
  end_offset_sec: EndOffsetSec;
  epoch_offset_sec: EpochOffsetSec;
  mapped_end_utc: MappedEndUtc;
  mapped_start_utc: MappedStartUtc;
  start_offset_sec: StartOffsetSec;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "DecisionConfig".
 */
export interface DecisionConfig {
  action_ids: ActionIds;
  allocation_order: AllocationOrder;
  default_request: EvaluationRequest;
  meta: Meta;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "DecisionHealth".
 */
export interface DecisionHealth {
  audit_status: AuditStatus;
  dataset_id: DatasetId1;
  schema_version?: SchemaVersion1;
  status: Status;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "ErrorInfo".
 */
export interface ErrorInfo {
  code: Code;
  details: Details;
  message: Message;
}
export interface Details {
  [k: string]: unknown;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "ErrorResponse".
 */
export interface ErrorResponse {
  error: ErrorInfo;
  schema_version?: SchemaVersion2;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "Evaluation".
 */
export interface Evaluation {
  actions: Actions;
  audit_status: AuditStatus1;
  baseline: Baseline;
  meta: Meta;
  portfolio: Portfolio;
  price_book_version: PriceBookVersion;
  ranking_basis: RankingBasis;
  request: EvaluationRequest;
  warnings: Warnings1;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "Portfolio".
 */
export interface Portfolio {
  allocation_order: AllocationOrder1;
  caveats: Caveats1;
  overlap_jobs: OverlapJobs;
  recoverable_gpu_hours: Estimate;
  reference_savings_usd: Estimate;
  risk: RiskResult;
  sample_capacity_gap_gpu_hours: Estimate;
  sample_capacity_target_fraction: SampleCapacityTargetFraction;
  sample_capacity_target_gpu_hours: SampleCapacityTargetGpuHours;
  selected_action_ids: SelectedActionIds1;
  unique_jobs: UniqueJobs;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "EvidencePage".
 */
export interface EvidencePage {
  action_id: ActionId1;
  limit: Limit;
  meta: Meta;
  next_offset: NextOffset;
  offset: Offset;
  rows: Rows;
  scope: Scope;
  total: Total;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "JobEvidenceRow".
 */
export interface JobEvidenceRow {
  candidate_gpu_hours: CandidateGpuHours1;
  capped_gpu_hours: CappedGpuHours;
  contribution_gpu_hours: Estimate;
  eligibility: Eligibility;
  finding_ids: FindingIds;
  gpu_count: GpuCount;
  job_id: JobId;
  measured_gpu_hours: MeasuredGpuHours2;
  nodes: Nodes;
  reasons: Reasons;
  state_name: StateName1;
  user_id: UserId;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "FindingDetail".
 */
export interface FindingDetail {
  causal_status: CausalStatus;
  description: Description;
  detector_id: DetectorId;
  evidence_origin: EvidenceOrigin1;
  finding_id: FindingId;
  impact_kind: ImpactKind;
  impact_scope: ImpactScope;
  job_ids: JobIds;
  meta: Meta;
  method: Method;
  node_names: NodeNames;
  reported_impact_gpu_hours: ReportedImpactGpuHours;
  resource_ids: ResourceIds;
  root_cause_ids: RootCauseIds;
  title: Title1;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "GpuDetail".
 */
export interface GpuDetail {
  capped_gpu_hours: CappedGpuHours1;
  gpu_id: GpuId;
  measured_gpu_hours: MeasuredGpuHours3;
  node: Node;
  quality_flags: QualityFlags;
  smutilization_pct_avg: SmutilizationPctAvg;
  smutilization_pct_max: SmutilizationPctMax;
  totalexecutiontime_sec: TotalexecutiontimeSec;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "Investigation".
 */
export interface Investigation {
  dataset_id: DatasetId2;
  evidence_origin: EvidenceOrigin2;
  finding_ids: FindingIds1;
  investigation_id: InvestigationId;
  limitations: Limitations;
  model_used: ModelUsed;
  nodes: Nodes1;
  nominal_drain_gpu_hours_24h: NominalDrainGpuHours24H;
  recommendation_id: RecommendationId;
  status: Status1;
  summary: Summary;
  token_usage: TokenUsage;
  tool_calls: ToolCalls;
  verdict: Verdict1;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "NodeAudit".
 */
export interface NodeAudit {
  cause: Cause;
  finding_ids: FindingIds2;
  node_name: NodeName;
  reasoning: Reasoning;
  reported_findings: ReportedFindings;
  resource_id: ResourceId;
  returned_findings: ReturnedFindings;
  scope_description: ScopeDescription;
  truncated: Truncated;
  verdict: Verdict;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "ToolCallRecord".
 */
export interface ToolCallRecord {
  arguments: Arguments;
  call_id: CallId;
  duration_ms: DurationMs;
  error: Error;
  result: Result;
  sequence: Sequence;
  started_at_utc: StartedAtUtc;
  status: Status2;
  tool_name: ToolName;
}
export interface Arguments {
  [k: string]: unknown;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "InvestigationResponse".
 */
export interface InvestigationResponse {
  investigation: Investigation;
  meta: Meta;
}
/**
 * This interface was referenced by `Track2DecisionContracts`'s JSON-Schema
 * via the `definition` "JobDetail".
 */
export interface JobDetail {
  array_job_id: ArrayJobId;
  attempts: Attempts;
  finding_ids: FindingIds3;
  gpus: Gpus;
  hit_node_failure: HitNodeFailure;
  job_id: JobId1;
  job_type: JobType;
  measured_gpu_hours: MeasuredGpuHours4;
  meta: Meta;
  nodefail_exact: NodefailExact;
  nodefail_nodes: NodefailNodes;
  quality_flags: QualityFlags1;
  sm_util_avg: SmUtilAvg;
  sm_util_max: SmUtilMax;
  state_name: StateName2;
  time_end_offset_sec: TimeEndOffsetSec;
  time_start_offset_sec: TimeStartOffsetSec;
  time_submit_offset_sec: TimeSubmitOffsetSec;
  user_id: UserId1;
  walltime_sec: WalltimeSec;
}
