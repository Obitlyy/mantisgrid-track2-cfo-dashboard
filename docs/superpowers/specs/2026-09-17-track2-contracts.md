# Track 2 统一契约 v1.0.0

状态：开发契约，实施时由步骤 1 创建类型与 fixtures；本文代码是规范片段，不代表代码已落地。适用规格：[开发规格](2026-09-17-track2-development-spec.md)。

## 1. 命名、版本与唯一来源

- Python 模块/函数/字段、JSON 字段：snake_case。TS 类型/组件：PascalCase；TS 本地变量 camelCase，但网络字段不转换。
- `schema_version="1.0.0"`；`analysis_version="track2-decision-v1"`。改变筛选、公式、归属顺序必须更新 analysis_version；改动字段/枚举须协调契约版本和消费者。
- 路由前缀唯一为 `/v1/decision`。禁止并存 `/decision-api`、`/analysis` 等第二套命名。
- 唯一行动枚举：`cpu_migration`、`idle_session_reclaim`。
- 唯一 Pydantic 类型源：`track-2/decision/contracts.py`。导出 `track-2/contracts/decision.schema.json`（总 bundle）、`track-2/contracts/openapi.json`（离线生成，不加载真实数据）。TS 从 schema 生成到 `track-2/dashboard/src/api/contracts.generated.ts`，禁止手写平行类型。
- 若JSON Schema编译器未为内联Literal产生具名ActionId，生成脚本追加 `export type ActionId = EvaluationRequest['selected_action_ids'][number];`；这是从已生成契约机械派生，不能手写另一份字符串union。
- 文档与实现冲突先由协调者修正契约并通知消费者；单个 agent 不得静默改共享字段。

## 2. 基础类型与请求

所有下列网络模型继承 `ContractModel`，`extra="forbid"`、`allow_inf_nan=False`。数值输入只接受 JSON number，拒绝字符串数字与 boolean。所有对象在响应中包含规定字段，未知值用 null，不用缺字段表示未知。

```python
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

ActionId = Literal["cpu_migration", "idle_session_reclaim"]
Origin = Literal["real_telemetry", "synthetic_incident", "test_fixture"]
Unit = Literal["gpu_hours", "usd", "cpu_core_hours", "job_hours"]

class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

class Bounds(ContractModel):
    low: float
    point: float
    high: float

class Estimate(Bounds):
    unit: Unit
    interval_kind: Literal["scenario"] = "scenario"
    confidence: None = None
    basis: str

class Pricing(ContractModel):
    usd_per_gpu_hour: float = Field(ge=0, le=1000000)
    usd_per_cpu_core_hour: float | None = Field(default=None, ge=0, le=1000000)

class CpuMigrationParameters(ContractModel):
    recoverable_fraction: Bounds
    additional_cpu_core_hours_per_gpu_hour: Bounds | None
    rerun_gpu_hours_per_candidate_gpu_hour: Bounds | None
    added_elapsed_hours_per_job: Bounds | None

class IdleSessionParameters(ContractModel):
    recoverable_fraction: Bounds
    rerun_gpu_hours_per_candidate_gpu_hour: Bounds | None
    added_elapsed_hours_per_job: Bounds | None

class EvaluationRequest(ContractModel):
    selected_action_ids: list[ActionId]
    pricing: Pricing
    cpu_migration: CpuMigrationParameters
    idle_session_reclaim: IdleSessionParameters
```

验证规则：Bounds 满足 `0 <= low <= point <= high`；recoverable_fraction 和 rerun_gpu_hours_per_candidate_gpu_hour 的 high ≤ 1；additional_cpu_core_hours_per_gpu_hour 的 high ≤ 1000000；added_elapsed_hours_per_job 的 high ≤ 1000000。selected_action_ids 不允许重复，允许空数组。纯粹零价格合法。上述限制需 model validators，不能仅依赖类型注解。

规范默认请求（示例参数为作者设定的情景，不是对真实回收比例的测量）：

```json
{
  "selected_action_ids": ["cpu_migration"],
  "pricing": {"usd_per_gpu_hour": 2.5, "usd_per_cpu_core_hour": null},
  "cpu_migration": {
    "recoverable_fraction": {"low": 0, "point": 0.5, "high": 1},
    "additional_cpu_core_hours_per_gpu_hour": null,
    "rerun_gpu_hours_per_candidate_gpu_hour": null,
    "added_elapsed_hours_per_job": null
  },
  "idle_session_reclaim": {
    "recoverable_fraction": {"low": 0, "point": 0.25, "high": 0.5},
    "rerun_gpu_hours_per_candidate_gpu_hour": null,
    "added_elapsed_hours_per_job": null
  }
}
```

默认 low 为零表示静态证据不能证明干预收益。UI 必须呈现 basis 和试点条件。不得把 50% 或 25% 写成“模型已验证回收率”。

## 3. 元信息、基线与行动响应

```python
class SampleWindow(ContractModel):
    start_offset_sec: float
    end_offset_sec: float
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
    state_name: str
    jobs: int
    measured_gpu_hours: float
    share_of_measured_gpu_hours: float
    reference_cost_usd: float

class Baseline(ContractModel):
    jobs: int
    gpu_rows: int
    measured_gpu_hours: float
    computed_proxy_gpu_hours: float
    completed_computed_proxy_gpu_hours: float
    non_completed_compute_share: float
    reference_cost_usd: float
    outcomes: list[OutcomeRow]
    caveats: list[str]

class ExclusionCount(ContractModel):
    reason: str
    jobs: int

class RiskResult(ContractModel):
    rerun_gpu_hours: Estimate | None
    rerun_reference_cost_usd: Estimate | None
    additional_cpu_core_hours: Estimate | None
    additional_cpu_cost_usd: Estimate | None
    added_job_hours: Estimate | None
    cash_savings_usd: None = None
    unknowns: list[str]

class Pilot(ContractModel):
    success_metrics: list[str]
    stop_conditions: list[str]
    rollback_steps: list[str]

class ActionEvaluation(ContractModel):
    action_id: ActionId
    title: str
    owner_role: str
    action: str
    effort: Literal["low", "medium", "high"]
    rank: int
    evidence_origin: Literal["real_telemetry", "test_fixture"]
    candidate_jobs: int
    candidate_gpu_hours: float
    excluded_jobs: int
    exclusion_counts: list[ExclusionCount]
    finding_count: int
    standalone_recoverable_gpu_hours: Estimate
    standalone_reference_savings_usd: Estimate
    marginal_recoverable_gpu_hours: Estimate | None
    marginal_reference_savings_usd: Estimate | None
    standalone_risk: RiskResult
    marginal_risk: RiskResult | None
    pilot: Pilot
    warnings: list[str]

class Portfolio(ContractModel):
    selected_action_ids: list[ActionId]
    allocation_order: list[ActionId]
    unique_jobs: int
    overlap_jobs: int
    recoverable_gpu_hours: Estimate
    reference_savings_usd: Estimate
    risk: RiskResult
    sample_capacity_target_fraction: float
    sample_capacity_target_gpu_hours: float
    sample_capacity_gap_gpu_hours: Estimate
    caveats: list[str]

class Evaluation(ContractModel):
    meta: Meta
    request: EvaluationRequest
    price_book_version: str
    baseline: Baseline
    actions: list[ActionEvaluation]
    portfolio: Portfolio
    ranking_basis: str
    audit_status: Literal["not_run", "running", "completed", "partial", "failed"]
    warnings: list[str]

class DecisionConfig(ContractModel):
    meta: Meta
    default_request: EvaluationRequest
    action_ids: list[ActionId]
    allocation_order: list[ActionId]
```

`candidate_*`、standalone 为单个行动独立观察；marginal 为当前组合分配后值，未选中行动的 marginal 三字段均 null。所有行动仍保留在 actions 中。价格版本读取官方 price book version，参数偏离官方 GPU 价则追加 `+custom`，不把参考价说成真实账单。

ID：`dataset_id` 为官方五文件的实际值级 SHA-256 按官方固定文件顺序串联后再做 SHA-256（每行 `relative_path + " " + digest + "\n"`），不能只 hash 清单文件；`evaluation_id` 为 dataset_id、analysis_version、规范化请求 JSON 的 SHA-256。selected_action_ids 按固定 allocation_order 规范排序后参与 hash；使用排序 key、紧凑 JSON、UTF-8、禁止非有限数。审计状态/时间戳不进入 evaluation_id，响应禁止声称它是整个 JSON 的字节哈希。

确切 evaluation hash 输入为 `json.dumps({"dataset_id": snapshot.dataset_id, "analysis_version": "track2-decision-v1", "request": normalized_request}, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")`。normalized_request 是 Pydantic 验证后的 model_dump，所有 ratio/price 等 float 字段归一为 float、负零变0.0，selected_action_ids 按固定顺序排序；因此 2 与2.0、选择顺序变更不会产生无意义的 revision。

## 4. 计算与归属规范

### 4.1 基线

`H_j = jobs.gpu_hours`，`u_j = clip(sm_util_avg, 0,100)/100`。

`A = sum(H_j)`；`C = sum(H_j*u_j)`；`CC = sum(H_j*u_j for COMPLETED)`；`non_completed_compute_share = 1-CC/A`。A 为零时该 share 返回 0 并附明确 empty-sample caveat，非空样本 A≤0 视为数据错误。`reference_cost_usd=A*price`。outcomes 按 `COMPLETED,CANCELLED,FAILED,TIMEOUT,NODE_FAIL,UNDECODED_11,UNDECODED_1024` 顺序列出（含零），其他 state_name 追加字典序；不丢失未匹配状态，映射为 `UNKNOWN` 并报告。

历史基线保持官方 measured 口径。缺失利用率不能按零声称无计算：真实官方数据若有缺失，返回 503 `DATA_INVALID` 并写明字段；扩展分析另开版本。所有汇总先完整精度求和，JSON 保留完整有限浮点数；金额只在 UI/claims 输出最终呈现时四舍五入。

### 4.2 候选与物理上限

官方 findings 是证据索引，不以它们的 impact 相加估计收益。候选需规则 predicate 和官方对应 finding 两者匹配；逐任务去重；历史分析包含 RESOLVED，不过滤 isActive。

- CPU：COMPLETED，mean=0 且 peak=0，measured GPU-hours >1；官方 detector `rules::gpu-not-needed`。
- Idle：`rules::idle-interactive-session` 或 `rules::slow-cancel-of-idle-job` 的并集；按官方规则复核 job_type、终态、时长>4h、mean<5%。这两个 finding 合并为一个行动，不能各自收钱。
- 共通质量门禁：`attempts==1`，walltime>0，有完整逐卡 join，duration 有限且非负，所有 card util 在 [0,100]，物理 key `(Node,gpu_id,id_job)` 唯一。requeue、缺 join、无效值归入排除清单，基线仍保留。
- 每卡 `cap_hours = min(totalexecutiontime_sec, walltime_sec)/3600`。正的超长读数截断并记录 warning；负值/NaN 不截成正常零值而排除该 job。
- `C_j = sum(cap_hours)`；CPU `B_cpu,j=C_j`。
- Idle 固定通知/宽限总门槛 4 小时（3.5h 提醒 +0.5h 宽限），`B_idle,j=min(C_j, gpu_count*max(walltime_sec/3600-4,0))`。这是后见情景容量上限，不是已测得的 idle tail；P0 门槛不是交互参数，变更须 analysis_version。

CandidateLedger 只收集 predicate 与官方对应 finding 均成立的原始候选；二者不一致的 job 计入 snapshot/analysis warning，若对当前两个行动的检测结果发生不一致则真实数据门禁失败 `DATA_INVALID`，不悄悄忽略。这不会要求无关规则可重算。每个行动 candidate_jobs/candidate_gpu_hours 只汇总质量合格行；excluded_jobs 为其原始候选中质量排除的 distinct job 数。exclusion_counts 可一 job 多理由，故各 reason 计数之和可能大于 excluded_jobs。

固定排除码：`REQUEUED_JOB`、`INVALID_WALLTIME`、`MISSING_GPU_ROWS`、`INVALID_GPU_DURATION`、`INVALID_GPU_UTILIZATION`、`GPU_COUNT_MISMATCH`、`CONTRADICTORY_ZERO_UTILIZATION`。CPU job 级 mean/peak 为零而任何 card 非零时使用最后一码。超长正 duration 仅标记 `DURATION_CAPPED`，不排除；重复 job 主键或物理 GPU key 是全局 `DATA_INVALID`，不得静默去重原始记录。EvidencePage.reasons 同时可出现 `OVERLAP_ASSIGNED_TO_CPU_MIGRATION`；quality_flags 可包含 `UNSAFE_SOURCE_IDENTIFIER`（float ID已丢失精度时不伪造恢复，nullable user/array ID显示未知；job 主键无法安全确定则数据门禁失败）。

### 4.3 组合去重与排序

固定归属顺序 `cpu_migration` → `idle_session_reclaim`。对 selected_action_ids 中的行动按此顺序遍历；一个 job 若已归属前项，后项整个 job 不再计益（也不重复计风险）。这是保守的整作业互斥策略；不把第一项未回收的比例余量再转给第二项。只选 idle 时其所有合格候选仍计入。

`overlap_jobs` 为被两个选中候选集合同时包含的 job 数。`unique_jobs` 为分配后的并集大小。`allocation_order` 为完整固定顺序，selected_action_ids 是其中的子序列。

推荐展示排序：standalone recoverable low 降序、point 降序、effort（low/medium/high）升序、action_id 字典序；rank 从 1 开始。不按 finding count/severity 排名，也不宣称风险未知时排序是“风险最优”。归属顺序与展示 rank 是不同概念。

### 4.4 收益、风险与未知值

设某个 standalone 或 assigned cohort 的候选容量总和 B，作业数 N，recovery fraction 三元组 f，rerun fraction 三元组 r，额外 CPU 系数 c，新增单任务 elapsed hours d：

```text
G[k] = B * f[k]                       k ∈ {low,point,high}
reference_savings_usd[k] = G[k] * gpu_price
R[k] = B * r[k]                       r 未提供则 R=null
rerun_reference_cost_usd[k] = R[k] * gpu_price
additional_cpu_core_hours[k] = G[k] * c[k]    CPU 行动，c 未提供则 null
additional_cpu_cost_usd[k] = additional_cpu_core_hours[k] * cpu_price
added_job_hours[k] = N * d[k]          d 未提供则 null；不是工程师闲置小时
```

c 与 f 的乘积区间是假设独立的非负范围包络；point 为两个 point 的积；不把它们叫概率分布。r 表示需要重跑的容量情景比例，并非“误判概率”。Idle 行动的 additional_cpu 两字段为零 Estimate 且 basis=`Not applicable to this action.`；这与 CPU 行动的未知成本不同。

组合收益为 assigned cohort 的 G 逐边界求和。组合风险每个字段分别合并：任一选中行动该字段未知，则该组合字段为 null，并在 unknowns 指明来源；空组合的各容量/成本风险为零（cash 仍 null），不能出现 NaN。所有 cash_savings_usd 固定 null，并说明没有账单兑现证据。现金节省不使用 GPU 参考金额减去模拟成本冒充。

组合 sample-capacity target 固定 `0.2*A`；gap.low=`max(target-G.high,0)`，gap.point=`max(target-G.point,0)`，gap.high=`max(target-G.low,0)`。UI 标签是 `Gap to 20% of sample GPU-hours`，必须说明非下一季度预算承诺。可将此次要指标折叠，不抢三张卡主叙事。

## 5. 证据模型

```python
class JobEvidenceRow(ContractModel):
    job_id: str
    user_id: str | None
    state_name: str
    gpu_count: int
    measured_gpu_hours: float
    capped_gpu_hours: float | None
    candidate_gpu_hours: float | None
    contribution_gpu_hours: Estimate
    eligibility: Literal["included", "excluded", "overlap_assigned_elsewhere"]
    reasons: list[str]
    finding_ids: list[str]
    nodes: list[str]

class EvidencePage(ContractModel):
    meta: Meta
    action_id: ActionId
    scope: Literal["standalone", "marginal"]
    rows: list[JobEvidenceRow]
    total: int
    offset: int
    limit: int
    next_offset: int | None

class GpuDetail(ContractModel):
    node: str
    gpu_id: int
    totalexecutiontime_sec: float | None
    smutilization_pct_avg: float | None
    smutilization_pct_max: float | None
    measured_gpu_hours: float | None
    capped_gpu_hours: float | None
    quality_flags: list[str]

class JobDetail(ContractModel):
    meta: Meta
    job_id: str
    user_id: str | None
    array_job_id: str | None
    state_name: str
    job_type: str | None
    attempts: int
    hit_node_failure: bool
    nodefail_nodes: list[str]
    nodefail_exact: bool
    time_submit_offset_sec: float | None
    time_start_offset_sec: float | None
    time_end_offset_sec: float | None
    walltime_sec: float | None
    measured_gpu_hours: float
    sm_util_avg: float | None
    sm_util_max: float | None
    finding_ids: list[str]
    gpus: list[GpuDetail]
    quality_flags: list[str]

class FindingDetail(ContractModel):
    meta: Meta
    finding_id: str
    detector_id: str
    title: str
    description: str
    resource_ids: list[str]
    root_cause_ids: list[str]
    job_ids: list[str]
    node_names: list[str]
    evidence_origin: Origin
    impact_scope: str | None
    impact_kind: str | None
    reported_impact_gpu_hours: float | None
    causal_status: Literal["available", "no_chain"]
    method: str
```

`contribution_gpu_hours` 按 scope 和相同 EvaluationRequest 计算；excluded/overlap 的 contribution_gpu_hours 为零 Estimate，有明示理由。无法计算 candidate ceiling 时，capped_gpu_hours/candidate_gpu_hours 为 null，排除行的 contribution_gpu_hours 仍为零 Estimate，以便贡献值合计与行动收益一致。action 未被选中且 scope=marginal 返回 422 `ACTION_NOT_SELECTED`，前端此时切 standalone。

EvidencePage 的行集合是当前行动的原始候选（通过 detector+predicate 但可未通过质量门禁），包括 excluded/overlap；按 job_id 十进制整数值升序，禁止按字符串字典序排序。offset≥total 返回空 rows 和 null next_offset。默认 limit=50，最大200，offset≥0。JobDetail.gpus 最大原始 job 的逐卡数，不截断。

job 关联只使用 metadata.job_id 或 resources 中 k8s:pod.resourceId，禁止从描述文本抽取 ID。node 名从 metadata.node 或 k8s:node.name。多任务/数组的 job_ids 只使用显式 `OWNS`/`CONTAINS` 关系展开，不得混淆数组 id 和 pod id。`primary_node` 不代表全部 placement，更不能替代 nodefail_nodes。

## 6. MCP 调查模型

```python
class ToolCallRecord(ContractModel):
    call_id: str
    sequence: int
    tool_name: str
    arguments: dict
    started_at_utc: str
    duration_ms: int
    status: Literal["success", "error", "timeout"]
    result: dict | None
    error: str | None

class NodeAudit(ContractModel):
    node_name: str
    resource_id: str
    cause: Literal["hardware", "user_code", "workload_mix", "cannot_determine"]
    verdict: Literal["inspect", "no_drain", "cannot_determine"]
    scope_description: str
    finding_ids: list[str]
    reported_findings: int
    returned_findings: int
    truncated: bool
    reasoning: str

class Investigation(ContractModel):
    investigation_id: Literal["node_recommendation_audit"]
    dataset_id: str
    status: Literal["not_run", "running", "completed", "partial", "failed"]
    verdict: Literal["accept", "revise", "reject", "cannot_determine"]
    evidence_origin: Literal["real_telemetry", "synthetic_incident", "mixed"]
    recommendation_id: str
    finding_ids: list[str]
    summary: str
    limitations: list[str]
    nodes: list[NodeAudit]
    nominal_drain_gpu_hours_24h: float
    tool_calls: list[ToolCallRecord]
    model_used: str | None
    token_usage: dict[str, int] | None

class InvestigationResponse(ContractModel):
    meta: Meta
    investigation: Investigation
```

原始 MCP structured result 可含官方 camelCase 字段，仅 ToolCallRecord.result 内允许；展示任何 ID 不作 JS number 算术。记录写盘时把已知数值型 ID 字段转为字符串，保留 `result` 作为语义等价标准化结果；未修改的协议原文仅存在本地 out 原始记录，不暴露到浏览器。error 清除路径中的密钥、认证头等敏感内容。

调查结果只作为证据解释，不直接修改两行动容量归属。原始数据不包含的 synthetic volume 场景在 UI 独立标注；不将它加入真实节省、hardware claims。

## 7. HTTP 路由与错误

| Method/path | 输入 | 输出 | 说明 |
|---|---|---|---|
| GET `/v1/decision/health` | 无 | `DecisionHealth` | 自建数据和契约 ready；独立于官方 `/health` |
| GET `/v1/decision/config` | 无 | `DecisionConfig` | 默认参数与可用行动，meta.evaluation_id=null |
| POST `/v1/decision/evaluate` | `EvaluationRequest` | `Evaluation` | 三张卡一次原子更新 |
| POST `/v1/decision/actions/{action_id}/evidence` | 同 EvaluationRequest；query scope/offset/limit | `EvidencePage` | meta.evaluation_id 与 evaluate 一致 |
| GET `/v1/decision/jobs/{job_id}` | 字符串路径；query dataset_id 必填 | `JobDetail` | meta.evaluation_id=null |
| GET `/v1/decision/findings/{finding_id}` | query dataset_id 必填 | `FindingDetail` | meta.evaluation_id=null |
| GET `/v1/decision/investigations/node_recommendation_audit` | query dataset_id 必填 | `InvestigationResponse` | 未跑返回 not_run，不伪装成功 |
| POST `/v1/decision/claims` | `ClaimsRequest` | `ClaimsResponse` | 仅返回 JSON，不写服务端根文件 |

```python
class DecisionHealth(ContractModel):
    status: Literal["ready", "not_ready"]
    schema_version: Literal["1.0.0"] = "1.0.0"
    dataset_id: str | None
    audit_status: Literal["not_run", "running", "completed", "partial", "failed"]

class ClaimsRequest(ContractModel):
    team: str
    evaluation_request: EvaluationRequest

class ClaimsResponse(ContractModel):
    meta: Meta
    claims: dict

class ErrorInfo(ContractModel):
    code: str
    message: str
    details: dict

class ErrorResponse(ContractModel):
    error: ErrorInfo
    schema_version: Literal["1.0.0"] = "1.0.0"
```

DecisionHealth 未 ready 为503且body仍为DecisionHealth，这是例外；其他路由错误均 ErrorResponse。官方路由保留官方错误格式，新路由验证错误要按前缀适配，不能全局破坏官方异常处理。

| HTTP | code | 明确行为 |
|---|---|---|
| 422 | `INVALID_REQUEST` | 非有限/越界/逆序区间、重复行动、未知字段、空白 team |
| 422 | `ACTION_NOT_SELECTED` | 请求未选择行动的 marginal 证据 |
| 404 | `NOT_FOUND` | 不存在的 job/finding/action；不得返回空成功对象 |
| 409 | `DATASET_MISMATCH` | detail query dataset_id 与服务当前数据不一致 |
| 503 | `DATA_NOT_READY` | 缺少数据文件 |
| 503 | `DATA_INVALID` | checksum 不一致、坏主键/利用率基线缺失等 |
| 500 | `INTERNAL_ERROR` | 日志记录堆栈；响应不包含堆栈/凭据 |

暂时没有异步用户任务、WebSocket、分页 token、自动重试写操作。重算是同步确定性请求；AbortController 及 latest-request 序号由前端防止竞态。服务端只缓存最多64个 Evaluation，LRU 按 evaluation_id；缓存清除不影响可重算性。

## 8. 内部 Python 接口（所有子任务使用原名）

```python
# decision/config.py
def resolve_paths() -> "RuntimePaths": ...
# RuntimePaths frozen dataclass: data_dir: Path, output_dir: Path

# decision/data.py
def load_snapshot(data_dir: "Path") -> "DataSnapshot": ...
# DataSnapshot frozen dataclass: dataset_id: str, jobs: DataFrame,
# gpus: DataFrame, resources: DataFrame, edges: DataFrame,
# findings: list[dict], sample_window: SampleWindow, data_origin: str
# DataFrames are treated read-only; any temporary columns require copy().

# decision/baseline.py
def compute_baseline(snapshot: "DataSnapshot", pricing: Pricing) -> Baseline: ...

# decision/candidates.py
def build_candidates(snapshot: "DataSnapshot") -> "CandidateLedger": ...
# CandidateLedger dataclass: rows: DataFrame, finding_index: dict[str, dict]
# rows: action_id(str), job_id(str), user_id(str|null), state_name(str),
# gpu_count(int), measured_gpu_hours(float), capped_gpu_hours(float|null),
# candidate_gpu_hours(float|null), eligible(bool), exclusion_reasons(list[str]),
# quality_flags(list[str]), finding_ids(list[str]), nodes(list[str]).
# Unique (action_id,job_id); eligible rows have finite nonnegative candidate hours.

# decision/portfolio.py
def allocate_candidates(ledger: "CandidateLedger", selected_action_ids: list[ActionId]) -> "Allocation": ...
# Allocation dataclass: owner_by_job: dict[str, ActionId], overlap_jobs: int

# decision/risk.py
def compute_risk(action_id: ActionId, candidate_gpu_hours: float,
                 candidate_jobs: int, request: EvaluationRequest) -> RiskResult: ...

# decision/service.py
def evaluate(snapshot: "DataSnapshot", request: EvaluationRequest,
             investigation: Investigation | None = None) -> Evaluation: ...
def evidence_page(snapshot: "DataSnapshot", request: EvaluationRequest,
                  action_id: ActionId, scope: str, offset: int, limit: int) -> EvidencePage: ...
def job_detail(snapshot: "DataSnapshot", job_id: str) -> JobDetail: ...
def finding_detail(snapshot: "DataSnapshot", finding_id: str) -> FindingDetail: ...

# decision/claims.py
def build_claims(evaluation: Evaluation, team: str) -> dict: ...

# decision/routes.py
# router: APIRouter with NO prefix; decision.app mounts prefix="/v1/decision" once.
def get_snapshot() -> "DataSnapshot": ...

# decision/validation.py (integration owner)
def validate_claims_semantics(claims: dict, evaluation: Evaluation) -> list[str]: ...

# decision/investigation.py (async; MCP agent owner)
async def run_investigation(data_dir: "Path", output_dir: "Path") -> Investigation: ...
def load_investigation(output_dir: "Path", dataset_id: str) -> Investigation | None: ...
```

这里的省略号是签名声明，不是允许遗漏的实现步骤。内部异常统一由 `decision/errors.py` 的 `DecisionError(code: str, message: str, details: dict, http_status: int)` 表达；route adapter 负责 ErrorResponse。

## 9. Claims 映射

`claims.team=team.strip()`；`recoverable_gpu_hours` 来自 portfolio.recoverable_gpu_hours；`recoverable_usd` 来自 portfolio.reference_savings_usd。导出 Estimate 时去掉 unit、confidence=null；保留 low/point/high、interval_kind、basis；basis 明确 sample/capacity/reference-price/scenario。不得增加未经调查的 node_triage/incident/hardware optional claims。

`cancelled_is_waste=false`，rationale 说明没有整体把 CANCELLED 当浪费，只有明确候选在显式情景下纳入。额外 `analysis_provenance` 字段由 schema 的 additionalProperties 允许，包含 dataset_id、evaluation_id、schema_version、analysis_version、完整 evaluation_request、reference_currency="USD"、cash_savings_claimed=false。该对象使评委可复算导出值。

对外 claims 数字在导出末端按 GPU-hours 6 位、USD 2 位 ROUND_HALF_UP 舍入；用 Decimal(str(value)) 实现；前端导出始终下载服务端 ClaimsResponse.claims，不自行重新计算。UI 显示的格式化误差与舍入位数需要在测试中说明。

## 10. 合约 fixtures 与最低一致性门禁

步骤1创建 `track-2/contracts/fixtures/` 共12份：`default-request.json`、`config.json`、`evaluation.json`、`evaluation-both-actions.json`、`evidence-cpu.json`、`evidence-idle.json`、`evidence-cpu-default.json`、`evidence-idle-standalone.json`、`job.json`、`finding.json`、`investigation.json`、`error-data-not-ready.json`。全部手工虚构，响应的 meta.data_origin 为 `test_fixture`（请求/错误无 meta，由 fixture 文件来源标记）；禁止从官方样本剪切。investigation 的 nested origin 描述虚构情景的类型，outer meta 和 limitations 明示 fixture，不冒充现场审计。详细手算账本见分析计划。

基础 fixture 用三个 job：101（CPU,10 GPU-h）、102（CPU+idle,20 GPU-h；idle ceiling=12）、103（idle,16 GPU-h；idle ceiling=8）。均为完整无异常单次 job；总 measured=46。默认 CPU f=(0,.5,1)，idle f=(0,.25,.5)。两项同时选择：CPU=0/15/30；idle marginal=0/2/4；组合=0/17/34，而 standalone 两项 point 之和为20。默认仅 CPU 时组合 point=15。GPU 价2.5时两项组合 reference point=42.5。这些数是测试样例，不能作为实际发现。

`evaluation.json` 对应默认仅 CPU 请求；`evaluation-both-actions.json` 对应 selected_action_ids 两项。`evidence-cpu.json`、`evidence-idle.json` 都采用两项请求和 scope=marginal（便于展示 overlap）。`evidence-cpu-default.json` 用默认CPU-only请求、scope=marginal，贡献point总和15；`evidence-idle-standalone.json` 用相同默认请求、scope=standalone，独立贡献point总和5。不能将不同scope/请求的fixture改ID冒充匹配。所有详情 fixture 的 dataset_id 与两份 evaluation 相同，详情的 evaluation_id=null。F1 在 `track-2/tests/factories.py` 暴露 `golden_snapshot() -> DataSnapshot` 和 `default_request() -> EvaluationRequest`，供 A2 测试共享。

`make contracts` 从 Pydantic 导出 schema、OpenAPI、TS；不得连接正式数据或启动 MCP。`make check-contracts` 重新生成到临时目录比较、校验所有 fixtures，任何差异失败。API 层还要检查真实响应可经 schema 验证、未知字段拒绝、日期映射、IDs 字符串不失真和 request→evaluation_id 稳定性。

可信期望清单保存在可跟踪 `track-2/contracts/official-checksums.txt`，原字节复制官方 `track-2/data/checksums.txt` 并在F1比较相等；根data/checksums.txt是第三份相同的评委操作副本。decision镜像包含/app/contracts，load_snapshot只信任包内/代码旁contracts的副本，不能用被挂载数据中的替换清单绕过官方检查。
