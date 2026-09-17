# Track 2 分析核心与 API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans 按本计划逐项实施；总计划已授权并行分工时使用其指定的执行方式。Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建可复算的两行动容量账本、组合收益与风险，并让英文看板和 claims 消费同一个 Evaluation。

**Architecture:** F1 提供只读 DataSnapshot、类型和公共错误；A2 完成纯函数分析，A3 适配 `/v1/decision` 路由。历史 measured GPU-hours、干预容量上限和情景收益分别保存；组合按 CPU → idle 整作业互斥归属。

**Tech Stack:** Python、pandas、Pydantic、FastAPI、pytest；版本及环境由 F1 的独立依赖锁定负责，本模块不升级官方依赖。

**Spec:** [开发规格](../../specs/2026-09-17-track2-development-spec.md)、[统一契约](../../specs/2026-09-17-track2-contracts.md)。发生冲突先协调契约，不在本计划创造第二套字段。

## 全局约束、入口门禁与文件所有权

- 工作根 `/Users/yiyangluo/Desktop/hackathon-2026-official-t1`；本文件是实施说明，不表示实现、真实数据分析或验证已经发生。
- `schema_version="1.0.0"`，`analysis_version="track2-decision-v1"`；两行动仅 `cpu_migration`、`idle_session_reclaim`。
- P0 所有区间 `interval_kind="scenario"`、`confidence=null`；`cash_savings_usd` 始终 null；默认低界为零，试点前不得声称已验证收益。
- findings 只提供证据索引；不得累计 `impact_gpu_hours`，不得按 severity、finding 数或固定 confidence 排收益。
- 所有公开文案英文；Slurm/用户/数组 ID 输出十进制字符串；不以 JS number 或浮点转换连接 ID。
- 真实行级派生记录只写忽略的 `out/`；保留官方五文件、生成器与校验清单，禁止 checksum `--write`。
- **F1 门禁：** `make check-contracts` 通过，公共模型、DataSnapshot loader、规范默认请求和手写 golden fixtures 已提交；F1 的失败不得用临时私有类型绕开。
- **A2 门禁：** 纯计算与 evidence 测试通过，手算结果与公共 fixtures 一致；前端可并行消费fixtures。A2先打通CPU，再完成idle；A3可在CPU稳定后编写路由，完整契约交付仍须双行动与去重全部通过。

| 负责人 | 文件与唯一职责 |
|---|---|
| F1，A2 只读消费 | `track-2/decision/{config,data,contracts,errors}.py`；`track-2/tests/factories.py`；`track-2/contracts/fixtures/*` |
| A2 | `track-2/decision/{baseline,candidates,portfolio,risk,service,claims}.py` |
| A2 测试 | `track-2/tests/analysis_fixtures.py`、`test_baseline.py`、`test_candidates.py`、`test_portfolio.py`、`test_risk.py`、`test_evidence.py`、`test_claims.py` |
| A3 | `track-2/decision/routes.py`、`track-2/tests/test_routes.py`、`test_decision_smoke.py` |
| 协调者，A3 提供接入说明 | `track-2/decision/app.py` 挂载 router、共享 Makefile、schema/OpenAPI 生成与最终报告 |
| MCP owner，A2/A3 只读消费 | `decision/investigation.py` 的 `load_investigation(output_dir, dataset_id)`；调查不改容量账本 |

执行测试前进入 F1 已准备的兼容 Python 环境；下列命令均从工作根执行。每个步骤先确认测试失败原因是当前缺失行为，再完成最小实现、运行对应测试并提交该模块拥有的文件；不使用 `git add .`。

## A2.1：冻结手算账本与测试输入

**依赖/接口：** F1 的 `tests/factories.py` 提供 `golden_snapshot() -> DataSnapshot`、`default_request() -> EvaluationRequest`；每次调用返回独立对象，不共享可变 DataFrame。以下测试显式导入这两个函数，不依赖未定义 pytest fixture。

| job_id | state_name / job_type | gpu_count | walltime h | H | mean / peak SM | CPU B | idle B |
|---|---|---:|---:|---:|---|---:|---:|
| `101` | COMPLETED / batch | 1 | 10 | 10 | 0 / 0 | 10 | — |
| `102` | COMPLETED / LLSUB:INTERACTIVE | 2 | 10 | 20 | 0 / 0 | 20 | 12 |
| `103` | CANCELLED / LLSUB:INTERACTIVE | 2 | 8 | 16 | 2 / 25 | — | 8 |

三作业 `attempts=1`；五 GPU 行各自 duration 等于所属 job walltime。CPU finding 覆盖 101/102，interactive 覆盖 102/103，slow-cancel 再覆盖 103；资源与边满足契约 joins。101/102 成功并不代表发生 GPU 计算。日期、graph 和 finding ID 使用 F1 fixture 的完整定义，不能另造不一致的副本。

默认 CPU f=(0,.5,1)，idle f=(0,.25,.5)，GPU 单价2.5，CPU 单价及全部风险参数 null。默认仅选 CPU；测试组合时显式 `model_copy(update={"selected_action_ids": ["cpu_migration", "idle_session_reclaim"]})`。

| 指标 | 手算期望 |
|---|---|
| baseline | jobs=3、gpu_rows=5、measured=46、completed=30、cancelled=16、reference_cost=115 |
| computed proxies | computed=.32、completed_computed=0、non_completed_compute_share=1 |
| standalone | CPU B=30，G=0/15/30；idle B=20，G=0/5/10 |
| 两项组合 | CPU owned={101,102}，idle owned={103}；unique_jobs=3，overlap_jobs=1 |
| marginal / portfolio | idle G=0/2/4；portfolio G=0/17/34；reference USD=0/42.5/85 |
| 默认 CPU-only | portfolio G=0/15/30；idle marginal 三字段为 null，standalone 仍可查看 |
| 20% 样本容量目标 | target=9.2，组合 gap=0/0/9.2；不称为季度现金目标 |

- [ ] 核对 F1 的 `evaluation.json` 是 CPU-only point=15；`evaluation-both-actions.json` 是组合 point=17；修订公共 fixture 由 F1 owner 操作。
- [ ] 核对证据fixtures：`evidence-cpu-default.json` 对应默认CPU-only request的marginal；`evidence-idle-standalone.json` 对应同request的idle standalone point=5；`evidence-cpu.json`/`evidence-idle.json` 对应both-actions request的marginal，分别point=15/2。请求、scope和evaluation_id不能混用。
- [ ] 新建 `analysis_fixtures.py`，仅定义本模块额外输入：`clone_snapshot(snapshot, *, jobs=None, gpus=None, resources=None, edges=None, findings=None) -> DataSnapshot`，未覆盖表深复制，保持元信息；测试变更行不得影响原 fixture。
- [ ] 定义 `risk_request() -> EvaluationRequest`：选两行动，CPU c=(.5,1,2)、r=(0,.1,.2)、d=(0,.5,1)，idle r=(0,.25,.5)、d=(0,1,2)，CPU 单价=.1，f 保持默认。该函数只构造契约模型，不计算期望结果。
- [ ] 为新增无关样本定义 `empty_snapshot() -> DataSnapshot`：沿用合法 SampleWindow、空但带类型的五表/列表、`data_origin="test_fixture"`；用于零分母与空候选测试。每个测试若需新 dataset_id，显式赋唯一 test-fixture 标记。
- [ ] 写入上述常量期望；运行 `PYTHONPATH=track-2 python -m pytest track-2/tests/test_baseline.py -q`，确认尚未实现的分析入口失败；测试不得读取官方数据。

## A2.2：历史基线与数据错误边界

**Files / 接口：** 新建 `baseline.py`，实现 `compute_baseline(snapshot: DataSnapshot, pricing: Pricing) -> Baseline`；消费 F1 `DecisionError`。测试 `test_baseline.py`。

- [ ] 从 jobs 一次遍历/向量化计算 `A=sum(H)`、`C=sum(H*clip(mean,0,100)/100)`、`CC=sum(COMPLETED 的 H*u)`；H 是原始 measured，不用 walltime×gpu_count 替换。
- [ ] 返回所有规范 outcomes（零项也保留），额外状态字典序追加；未匹配状态归 UNKNOWN，记录数量/覆盖 caveat；总 jobs 和总 measured 必须守恒。
- [ ] A=0 且空样本返回 share=0 与 empty-sample caveat；非空 A≤0、非有限 H 或基线 mean 缺失返回503。例如缺 mean 使用 `DecisionError(code="DATA_INVALID", message="Missing baseline SM utilization.", details={"field": "sm_util_avg", "invalid_jobs": invalid_count}, http_status=503)`，invalid_count 是本次字段检查计数，不输出整行数据。
- [ ] 实现 price=0 的合法结果；完整精度求和，不逐行 round；不把 `.mean()` 得到的行均值替代 GPU-hour 加权值。

```python
import pytest
from decision.baseline import compute_baseline
from factories import golden_snapshot, default_request

def test_baseline_conserves_measured_hours():
    b = compute_baseline(golden_snapshot(), default_request().pricing)
    assert (b.jobs, b.gpu_rows) == (3, 5)
    assert b.measured_gpu_hours == 46
    assert sum(x.measured_gpu_hours for x in b.outcomes) == 46
    assert b.computed_proxy_gpu_hours == pytest.approx(.32)
    assert b.completed_computed_proxy_gpu_hours == 0
    assert b.non_completed_compute_share == 1
    assert b.reference_cost_usd == 115
```

- [ ] 添加 empty、UNKNOWN、缺 mean、非有限 H、零价格断言；对官方 Store 因空 state 被过滤的口径差异给 caveat，不静默删行追平官方。
- [ ] 运行 `PYTHONPATH=track-2 python -m pytest track-2/tests/test_baseline.py -q`；只在通过后提交 baseline 与其测试。

## A2.3：候选、逐卡上限与证据索引

**Files / 接口：** `candidates.py` 定义契约规定的 `CandidateLedger`，实现 `build_candidates(snapshot: DataSnapshot) -> CandidateLedger`；测试 `test_candidates.py`。Ledger 列名、dtype 与空表列结构严格按契约第8节。

- [ ] 建 finding_index，以 finding.id 唯一；建立 pod resourceId → job、node resource name、OWNS/CONTAINS 的显式索引。优先使用可信整数/十进制字符串，不从 prose 抽 ID；metadata 与资源映射冲突返回数据错误，不能猜。
- [ ] CPU 需对应 detector **且** COMPLETED、mean=peak=0、H>1；idle 为两个对应 detector 的并集，分别复核 interactive 或 CANCELLED、walltime>4h、mean<5%。RESOLVED 仍纳入；两行动 predicate/finding 不一致记录诊断并以 DATA_INVALID 阻止真实数据门禁，不能悄悄缩小分母。
- [ ] 同 action/job 合并 finding_ids；103 的 interactive 与 slow-cancel 产生一行。`finding_count` 为行动原始候选关联的不同 finding ID 数，包含其质量排除证据；CPU=2、idle=3，不作为收益系数。
- [ ] 联接 GPU 到 job 使用完整物理 key、many_to_one 验证与每 job 行数==gpu_count；检查 attempts、正 walltime、duration 有限非负、card avg/max 有限且在[0,100]。CPU job声称零mean/peak而card非零时排除，不能根据聚合数据覆盖逐卡冲突。
- [ ] `candidate_jobs`/`candidate_gpu_hours` 仅合格 standalone ledger 行；`excluded_jobs` 为质量失败的原始候选 job 去重数，多个 exclusion_counts 可同时描述同一 job，因此不得把它们相加当总排除数。
- [ ] 每卡 cap=min(duration,walltime)/3600；超长正读数标 quality warning，保留 raw measured；负/缺 duration 排除整 job。CPU B=sum(card cap)；idle B=min(C,gpu_count×max(walltime/3600−4,0))。
- [ ] requeue 仍保留历史 H、job detail 与排除理由；不得用最后 attempt 的 placement 拼接混合 GPU rows，或把 nodefail_nodes 改成 primary_node。
- [ ] 当前两行动 metadata缺失/连接冲突导致不能确认 predicate 时，返回 DATA_INVALID 与定位信息；无关规则的缺失不强行要求全部可重算。非有限详情字段序列化为 null 并带 quality flag，不把无效值伪造为正常0。

| 输入问题 | 精确账本/错误行为 |
|---|---|
| attempts≠1 / walltime无效 | `REQUEUED_JOB` / `INVALID_WALLTIME`；job按质量排除 |
| 无逐卡记录 / 行数≠gpu_count | `MISSING_GPU_ROWS` / `GPU_COUNT_MISMATCH` |
| duration负值或缺失 / card util无效 | `INVALID_GPU_DURATION` / `INVALID_GPU_UTILIZATION` |
| CPU零聚合与非零card冲突 | `CONTRADICTORY_ZERO_UTILIZATION` |
| duration正且超长 | `DURATION_CAPPED` quality warning；仍可纳入截断容量 |
| 重复job或物理GPU key | 全局503 `DATA_INVALID`，不得静默去重 |
| float已丢失ID精度 | `UNSAFE_SOURCE_IDENTIFIER`；user/array可null，job主键不安全则DATA_INVALID |

```python
from decision.candidates import build_candidates
from factories import golden_snapshot

def test_candidate_grain_and_tail():
    ledger = build_candidates(golden_snapshot())
    rows = ledger.rows.set_index(["action_id", "job_id"])
    assert rows.index.is_unique
    assert rows.loc[("cpu_migration", "102"), "candidate_gpu_hours"] == 20
    assert rows.loc[("idle_session_reclaim", "102"), "candidate_gpu_hours"] == 12
    assert rows.loc[("idle_session_reclaim", "103"), "candidate_gpu_hours"] == 8
    assert len(rows.loc[("idle_session_reclaim", "103"), "finding_ids"]) == 2
```

- [ ] 在 clone_snapshot 副本逐一构造 strict 边界：H=1 不命中 CPU，4h/5% 不命中 idle，avg=0 但 peak>0 不命中 CPU；同步调整对应finding和逐卡输入以测试合法非候选，另留不调整finding的版本明确断言DATA_INVALID。缺peak不按0处理。
- [ ] 构造 walltime2h、两卡duration3h/1h：raw H=4、cap=3，确认基线仍4；另测负值、NaN、缺 GPU、重复物理 key、attempts=2。坏全局主键由 F1 loader 拒绝；候选专属质量问题按排除账本返回。
- [ ] 使用独立相邻大 ID `9007199254740992`、`9007199254740993` 更新 jobs/GPU/pod/finding 的全部连接，确认两条证据不合并。另测不安全user/array返回null和flag、job主键不安全返回DATA_INVALID。
- [ ] 运行 `PYTHONPATH=track-2 python -m pytest track-2/tests/test_candidates.py -q`；交付 ledger 给 A2.4/A2.6，未经计算的官方文档总量不得硬编码。

## A2.4：组合归属、收益、稳定排序与身份

**Files / 接口：** `portfolio.py` 定义 `Allocation(owner_by_job, overlap_jobs)`，实现 `allocate_candidates(ledger, selected_action_ids) -> Allocation`；`service.py` 实现 `evaluate(snapshot, request, investigation=None) -> Evaluation`。测试 `test_portfolio.py`。

- [ ] 只向合格行分配所有者，固定 CPU→idle；选中两项时102始终归 CPU，即使 CPU f=0 或 idle 展示 rank 更高。整 job 被占后不将未回收比例再转给 idle。
- [ ] 对每项分别求 standalone B/N 与 assigned B/N；每个边界 G=B×f；未选中行动仍返回 standalone，marginal 收益/美元/风险均 null。全部 Estimate 明示 basis 为场景、非观察到的节省。
- [ ] 组合逐边界累计 assigned G；target=.2A；gap 使用 high/point/low 反向对应，保证 bounds 顺序。空组合收益全0、unique/overlap全0，gap 全9.2（golden）。
- [ ] 展示 rank 按 standalone low↓、point↓、effort↑、action_id↑；固定 allocation_order 不随 rank 改变。默认 low 均0时按 point 排名，不声称“风险最优”。
- [ ] 用契约规范化请求与哈希对象生成 evaluation_id；selected_action_ids 按 allocation_order 排序，float字段统一float、负零归0.0；以 `{"dataset_id": snapshot.dataset_id, "analysis_version": "track2-decision-v1", "request": normalized_request}` 按sorted keys、紧凑JSON、UTF-8、allow_nan=False做SHA-256。2/2.0和选择顺序不改ID；价格/风险参数改变会改ID；审计状态/时间不进入ID。dataset_id直接消费F1实际值级身份。
- [ ] GPU 价异于官方 price book 默认值才追加 `+custom`；风险 CPU 价无需伪造账单版本。evaluation 保留规范请求，不能只记录最终美元。

```python
import pytest
from decision.service import evaluate
from factories import golden_snapshot, default_request

def test_exclusive_portfolio_does_not_sum_standalone():
    req = default_request().model_copy(update={"selected_action_ids": [
        "cpu_migration", "idle_session_reclaim"]})
    result = evaluate(golden_snapshot(), req)
    assert sum(a.standalone_recoverable_gpu_hours.point for a in result.actions) == 20
    assert result.portfolio.recoverable_gpu_hours.point == 17
    assert result.portfolio.recoverable_gpu_hours.high == 34
    assert result.portfolio.reference_savings_usd.point == 42.5
    assert (result.portfolio.unique_jobs, result.portfolio.overlap_jobs) == (3, 1)
    assert result.portfolio.sample_capacity_target_gpu_hours == pytest.approx(9.2)
```

- [ ] 测 CPU-only=15、idle-only=5、空选=0；选择顺序颠倒结果身份相同；价格翻倍所有已知 GPU 美元翻倍而 B/G 不变；同 snapshot 重复调用无 DataFrame 改动。
- [ ] 运行 `PYTHONPATH=track-2 python -m pytest track-2/tests/test_portfolio.py -q`；交付 CPU-only 与 both-actions 的模型结果给 F1 fixture owner/frontend owner。

## A2.5：风险、未知传播与试点条件

**Files / 接口：** `risk.py` 实现 `compute_risk(action_id, candidate_gpu_hours, candidate_jobs, request) -> RiskResult`；组合字段合并在 service.py；测试 `test_risk.py`。

- [ ] 对同一 standalone/assigned cohort 使用 R=B×r、replay USD=R×GPU价、CPU core-hours=G×c、CPU成本=core-hours×CPU价、added_job_hours=N×d。r 是重跑容量比例，不是错误概率；d 是 job elapsed 增量，不是员工闲置时间。
- [ ] 参数缺失返回相应 null，unknowns 列明 action/字段。已知 core-hours 但缺 CPU价只使 cost 未知；GPU价=0不把未知 rerun 变已知0。idle 的两个 additional_cpu 字段用零 Estimate，basis 精确 `Not applicable to this action.`。
- [ ] 组合逐字段：任一选中行动该字段未知则合计 null；选中但 assigned 空的行动仍遵循参数未知规则。只有完全空组合各非 cash 风险为零；cash 永远 null，说明缺少账单兑现证据。
- [ ] 用 A2.1 risk_request 手算：CPU R=0/3/6、CPU core-hours=0/15/60、CPU成本=0/1.5/6、added_job_hours=0/1/2；idle marginal R=0/2/4、added_job_hours=0/1/2。组合 R=0/5/10、rerun USD=0/12.5/25、added_job_hours=0/2/4。

```python
from decision.service import evaluate
from factories import golden_snapshot, default_request
from analysis_fixtures import risk_request

def test_risk_unknown_is_not_zero():
    unknown = evaluate(golden_snapshot(), default_request()).portfolio.risk
    assert unknown.rerun_gpu_hours is None
    assert unknown.additional_cpu_cost_usd is None
    assert unknown.cash_savings_usd is None
    known = evaluate(golden_snapshot(), risk_request()).portfolio.risk
    assert known.rerun_gpu_hours.point == 5
    assert known.rerun_reference_cost_usd.point == 12.5
    assert known.additional_cpu_core_hours.high == 60
    assert known.added_job_hours.point == 2
```

- [ ] CPU Pilot 文案含输出正确性、CPU队列容量、完成时长、GPU重跑；无 checkpoint 信息时不猜恢复成本。停止条件为输出不一致或预先约定的时长/重跑限额超标；回滚到原队列与资源请求。
- [ ] idle Pilot 文案含3.5h提醒+.5h宽限、owner确认、rolling SM/liveness/user activity/checkpoint 数据需求；告知 lifetime predicate 后见性。发生有效任务误中断即停止自动回收试点，恢复分配并复核保护条件。
- [ ] 固定 owner_role 为职能（如 Platform engineering / Research platform operations），不伪装真实负责人。误行动损失、未行动机会和名义节点停用容量分开解释，不额外加入未授权第三行动。
- [ ] 运行 `PYTHONPATH=track-2 python -m pytest track-2/tests/test_risk.py -q`；边界乘积是非负情景包络，文案不能称统计置信区间。

## A2.6：证据分页与 claims 同源导出

**Files / 接口：** service.py 的 `evidence_page(snapshot, request, action_id, scope, offset, limit)`、`job_detail(snapshot, job_id)`、`finding_detail(snapshot, finding_id)`；claims.py 的 `build_claims(evaluation, team) -> dict`。测试 `test_evidence.py`、`test_claims.py`。

- [ ] EvidencePage 展示 detector+predicate 的原始候选，含 quality excluded 和 overlap；按 ID 整数值排序，50默认/200上限，offset≥total为空。每页 evaluation_id 与同 request evaluate 完全相同。
- [ ] 同 job standalone/marginal 使用同 B 但不同 contribution；102 的 idle marginal 为 overlap_assigned_elsewhere、零 contribution、保留 B=12，reasons含 `OVERLAP_ASSIGNED_TO_CPU_MIGRATION`；103的marginal point=2。无法计算cap/B保持null，excluded contribution为零。
- [ ] 未选 action 请求 marginal 抛 `ACTION_NOT_SELECTED`；详情是 dataset scope，meta.evaluation_id=null。JobDetail 保留全部物理卡行及原始nodefail字段；FindingDetail 区分真实/合成/test来源，以root_cause_ids是否存在区分available/no_chain，不把可调查的链接冒充实际已完成MCP调查。
- [ ] 测各页合计 contribution 等于相同 scope 的行动收益；加入 job IDs "2"/"10" 验整数排序；不存在 job/finding 抛 NOT_FOUND。完整图 joins 回溯到同 job ID，不能用 primary_node 替代逐卡 placement。
- [ ] claims 映射 portfolio；team.strip且非空；导出 low/point/high、interval_kind、basis，去 unit/null confidence。加入完整 analysis_provenance，cash_savings_claimed=false，cancelled_is_waste=false与英文理由；无调查的 optional node/incident/hardware 字段不输出。
- [ ] 最终用 Decimal(str(value)) / ROUND_HALF_UP：GPU小时6位、USD2位。测1.2345675→1.234568、2.675→2.68；组合 point=17、USD point=42.50，CPU-only point=15。
- [ ] 运行 `PYTHONPATH=track-2 python -m pytest track-2/tests/test_evidence.py track-2/tests/test_claims.py -q`；claims HTTP只返回JSON，写根文件由最终交付流程负责。

## A3：路由集成、真实数据烟测与交接

**依赖：** F1 schema门禁通过、A2的CPU计算稳定后可开始路由工作；G3-A交付前A2全部测试通过，不构造尚未实现的idle收益。`routes.py` 提供 `router: APIRouter`，由协调者在decision.app挂载。提供 `get_snapshot() -> DataSnapshot` 依赖函数供FastAPI dependency_overrides；真实加载只在请求/启动生命周期，离线schema导出不得读数据。

| 方法与完整路径 | 输入与输出 |
|---|---|
| GET `/v1/decision/health` | 无输入 → DecisionHealth |
| GET `/v1/decision/config` | 无输入 → DecisionConfig |
| POST `/v1/decision/evaluate` | EvaluationRequest → Evaluation |
| POST `/v1/decision/actions/{action_id}/evidence` | EvaluationRequest；query scope/offset/limit → EvidencePage |
| GET `/v1/decision/jobs/{job_id}` | 必填query dataset_id → JobDetail |
| GET `/v1/decision/findings/{finding_id}` | 必填query dataset_id → FindingDetail |
| GET `/v1/decision/investigations/node_recommendation_audit` | 必填query dataset_id → InvestigationResponse |
| POST `/v1/decision/claims` | ClaimsRequest → ClaimsResponse |

- [ ] router本身不声明prefix，由协调者统一 `app.include_router(router, prefix="/v1/decision")`，只添加一次；路由级错误适配包装保证下面的独立FastAPI测试也得到ErrorResponse。
- [ ] 所有 detail query 要求 dataset_id；不一致409 DATASET_MISMATCH。action path先按字符串接受再校验存在性，不让未知行动路径错误变成框架默认422。
- [ ] 适配缺文件503 DATA_NOT_READY、损坏数据503 DATA_INVALID、请求422 INVALID_REQUEST、未选行动422 ACTION_NOT_SELECTED、找不到404 NOT_FOUND、内部500 INTERNAL_ERROR；仅新前缀使用 ErrorResponse，官方异常格式不变。
- [ ] `health` ready/not_ready 使用 DecisionHealth，未ready HTTP503；`config` meta.evaluation_id=null。请求 strict validators 拒绝 bool/字符串数字、逆序区间、NaN/Infinity、未知字段、重复行动、空白team；零价和空选择合法。
- [ ] evaluate/evidence使用同一只读snapshot，最多64项LRU按evaluation_id缓存；审计状态从匹配dataset的 load_investigation读取并更新，不把旧缓存中的audit_status当成当前状态。未运行not_run，真实失败不得标completed。
- [ ] test_routes.py 用 TestClient + dependency_overrides[get_snapshot]=golden_snapshot，测试规范默认请求、组合17、evidence102 overlap、missing dataset、mismatch、未知ID和所有错误码；验证JSON响应无非有限数并通过导出schema。

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
from decision.routes import router, get_snapshot
from factories import golden_snapshot, default_request

def test_invalid_request_has_project_error_shape():
    app = FastAPI()
    app.include_router(router, prefix="/v1/decision")
    app.dependency_overrides[get_snapshot] = golden_snapshot
    payload = default_request().model_dump(mode="json")
    payload["pricing"]["usd_per_gpu_hour"] = True
    with TestClient(app) as client:
        response = client.post("/v1/decision/evaluate", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
```

- [ ] 调用 `POST /v1/decision/claims`，确认返回值与直接 `build_claims(evaluate(snapshot, request), team)` 完全相同；服务端根目录没有新增claims文件。
- [ ] test_decision_smoke.py 加 `real_data` marker，由协调者注册marker；没有显式TRACK2_DATA_DIR时skip，不在collection读取文件。显式运行时载入resolve_paths/load_snapshot，验证实际checksum身份、measured outcome守恒、card→job总量一致、两候选predicate、去重上限、detail分页可追溯。无候选时允许0并要求说明，不用文档计数强行断言。
- [ ] 真实烟测记录实际值但不提交真实行；对官方 efficiency summary 复核同覆盖下 A/C/CC，若UNKNOWN造成覆盖差异则报告差异。真实MCP调查由其owner运行，分析层不伪装已调用MCP。

以下为**实施后**的命令，不是本次规划执行记录：

```bash
make check-data
make check-contracts
PYTHONPATH=track-2 python -m pytest track-2/tests/test_baseline.py track-2/tests/test_candidates.py track-2/tests/test_portfolio.py track-2/tests/test_risk.py track-2/tests/test_evidence.py track-2/tests/test_claims.py track-2/tests/test_routes.py -q
MGAI_DATA_DIR="$PWD/data" TRACK2_DATA_DIR="$PWD/data" TRACK2_OUTPUT_DIR="$PWD/out" PYTHONPATH=track-2 python -m pytest track-2/tests/test_decision_smoke.py -m real_data -q
curl --fail-with-body http://localhost:3000/v1/decision/health
curl --fail-with-body http://localhost:3000/v1/decision/config
```

- [ ] 交前端：统一 schema/默认请求、CPU-only与both-actions fixtures、standalone与marginal切换规则、null风险与excluded证据文案；前端不重算金额。
- [ ] 交MCP owner：dataset_id与FindingDetail连接规则、真实/合成隔离、审计不改收益约束；MCP结果只有同dataset才挂到Evaluation。
- [ ] 交协调者：A2/A3拥有文件、测试命令和结果、实际烟测摘要、仍未知的风险字段；由其运行make contracts/集成路由/最终claims校验并更新报告。
- [ ] 验收：46/17/42.5手算通过；真实基线可复算、收益不双计、现金全null；全部金额→行动→finding→job→GPU路径可追；没有真实行级fixture、无授权外代码/依赖改动、无未证实节省承诺。
