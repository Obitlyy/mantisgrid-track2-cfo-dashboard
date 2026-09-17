# Track 2 MCP 调查实施计划

> **For agentic workers:** 实施时使用 superpowers:subagent-driven-development 或 superpowers:executing-plans；复选框对应实际实现和验证。M2 可在 F1通过后与 A2/U2并行。

**Goal:** 用实际官方 MCP 工具调查“按 finding 数量停用前五节点”的建议，给出可审计的证据和局限。

**Architecture:** Python FastMCP Client 通过 stdio 启动官方 `mcp_layer.server`；受限工具序列写入本地 out，decision API读取冻结模型。MCP运行独立于基础收益计算。

**Tech Stack:** 现有 Python/FastAPI/FastMCP，asyncio、JSON、SHA-256；使用F1扩展锁，不自行更换 FastMCP版本。

**Spec:** [开发规格](../../specs/2026-09-17-track2-development-spec.md)、[统一契约](../../specs/2026-09-17-track2-contracts.md) §6–8；官方 `track-2/mcp_layer/README.md`、`api/main.py` 的 causal/recommendations 实现。

## Global Constraints

- 不把 HTTP GET/直接调用 Python route 写成“执行了MCP”。必须存在协议客户端真实 tools/list 与 tools/call。
- 调查是 read-only；不执行 drain/cancel，不把模型固定confidence解释为概率。
- 不修改官方 server/工具语义，不新增第二套字段。Root/MCP路径使用 F1 的 MGAI_DATA_DIR。
- 本模块只写 investigation.py、mcp_client.py、audit_storage.py及自己的测试；app/bootstrap/cli由协调者接线。
- 明确区分未运行、失败、有限覆盖与完整执行。mock测试记录只能是 test_fixture。

## 1. 依赖和产物

**输入：** F1的 RuntimePaths/DataSnapshot、契约 ToolCallRecord/NodeAudit/Investigation、完整数据、已锁定 FastMCP。

**输出：**

```python
async def run_investigation(data_dir: Path, output_dir: Path) -> Investigation:
    ...

def load_investigation(output_dir: Path, dataset_id: str) -> Investigation | None:
    ...
```

结果ID固定 `node_recommendation_audit`，recommendation_id读取官方响应中的 `rec_drain_nodes`；不存在则 verdict=cannot_determine，不能根据标题模糊匹配。model_used/token_usage 为 null，因为 P0 使用确定性调查脚本，不调用LLM。

产物路径：`out/mcp/<dataset_id>/node_recommendation_audit.json`；协议原文 `out/mcp/<dataset_id>/raw/<call_id>.json`。两者均被忽略。正式响应只展示标准化脱敏 ToolCallRecord，不包含环境变量/认证信息。缓存有效性同时检查 schema_version（外层存储envelope）、analysis_version、dataset_id。

## 2. 固定执行预算

| 项目 | 值 |
|---|---|
| 整次审计墙钟预算 | 120秒，包含子进程启动 |
| 单次工具调用预算 | 20秒，受总剩余时间约束 |
| tools/call次数上限 | 25 |
| 节点 | 最多5个 |
| 每节点 finding分页 | 最多2页，每页100 |
| findings 调用总额 | 最多10次，包含为演示有链案例而做的detector过滤调用 |
| causal | 最多8次，包含1次无链案例（若有） |
| neighbor | 最多3次，hop_count=1 |
| 自动重试 | 0；失败记录真实状态，可通过 make audit显式重跑 |
| 同一 dataset 并发审计 | 1，文件锁；另一调用复用有效缓存或返回正在运行 |

tools/list握手必须记录在日志，预算25指业务 tools/call；不得无限循环分页/递归图遍历。返回超过范围的输入先校验，节点按返回顺序和resource_id稳定去重。

调度器须预留有链案例的查找名额；若top节点已提供合适链则将名额用于节点第二页。4次基础调用+最多10次findings+8次causal+3次neighbor=25。每节点最多2页是上限，不保证每节点都取得2页；因此返回数与truncated必须来自实际调用。

## Task M2.1：协议客户端与可观测调用

**Files:** Create `track-2/decision/mcp_client.py`, `track-2/tests/test_mcp_client.py`。

**Interfaces:** `McpSession` 为 async context manager；`call(tool_name: str, arguments: dict) -> ToolCallRecord`；构造时接收 data_dir:Path、remaining budget和已锁定可执行路径。进程命令使用当前解释器 `sys.executable -m mcp_layer.server`，cwd为包含 `api/`、`mcp_layer/` 的代码根；env只覆盖 MGAI_DATA_DIR，保留必要PATH。

- [ ] 先按锁定SDK的实际签名确认 `Client`、stdio transport、structured result和isError；将适配封装在这个文件，其他模块不得依赖SDK版本细节。
- [ ] 新增 fake transport单元测试：成功dict、文本JSON、非JSON文本、isError、超时；fake transport不能被标记为真实运行。
- [ ] 用 `asyncio.timeout` 限制调用；序号单调递增，duration_ms 使用 monotonic clock，started_at_utc 使用UTC RFC3339。
- [ ] result标准化：优先structured_content；否则解析text JSON；既无结构也无合法JSON时保留error而不是猜测数据。
- [ ] context退出、取消或失败必须关闭stdio并终止自建子进程；不杀其他任务的MCP。
- [ ] 实现以下实际调用方式的版本适配，再用真实health验证：

```python
# client构造细节按锁定FastMCP适配在McpSession内，调用者只认本接口。
async with McpSession(data_dir=data_dir, total_timeout_sec=120) as session:
    receipt = await session.call("health", {})
    if receipt.status != "success":
        return failed_investigation(receipt)
```

这里 `failed_investigation(receipt)` 是本任务需在 investigation.py 实现的内部构造函数：返回 status=failed、verdict=cannot_determine、nodes=[]、nominal_drain_gpu_hours_24h=0、包含receipt与失败说明，其余字段依契约；不进行进一步调用。

Run: `make test-api TEST_ARGS='track-2/tests/test_mcp_client.py -q'`。Expected：上述五种结果和进程回收通过。真实 `make audit` 在 M2.3后运行。

## Task M2.2：确定性调查策略

**Files:** Create `track-2/decision/investigation.py`, `track-2/tests/test_investigation.py`。

**Consumes:** McpSession、DataSnapshot资源映射、官方工具返回。**Produces:** Investigation。

- [ ] 顺序调用 `health({})`、`list_rules({})`、`recommendations({"usd_per_gpu_hour":2.5})`、`underperforming({"entity_type":"node","limit":5,"usd_per_gpu_hour":2.5})`。价格从官方price book默认对象读取，2.5为当前值，不能在多处硬编码。
- [ ] 取 rec_drain_nodes，解析underperforming rows中的resource_id/名称，按 resources真实类型确认k8s:node。字段具体来自官方 models/路由，不从标题解析。
- [ ] 每节点执行 `list_findings({"resource_id":rid,"limit":100,"offset":0})`；若total>100再请求offset100。保存total、unique返回数、截断状态；不只读recommendation前20个引用。
- [ ] 将 findings按id去重，用(rootCause resource id, detector族, 窗口/episode字段)选择有链代表；优先hardware、array/user burst、合成volume分别保留。剩余名额按 finding_id 排序；上限8。
- [ ] 至少有一个无链finding时分配一个causal调用，验证“findings=[]”是正常结果；没有则记录不适用，不能编造。
- [ ] 在有根因证据时调用最多3个neighbor，hop_count=1；500节点截断限制不能当成完整拓扑。
- [ ] 结合本地prepped数据验证相应节点/窗口的作业、用户、阵列暴露，不能只复述工具自然语言。查询的分母、字段和限制写进NodeAudit.reasoning；若预算内无法完成则cannot_determine。
- [ ] 每条NodeAudit.scope_description说明观察窗口，拒绝把某次阵列失败归因推广成整个节点永远健康。
- [ ] `nominal_drain_gpu_hours_24h = distinct_proposed_nodes * 2 * 24`，仅是名义移除容量，UI不得把它当实际生产损失。

判定表：

| 证据 | NodeAudit.cause | verdict | 解释限制 |
|---|---|---|---|
| 同窗口多独立用户/任务集中该机异常，有原始对照与hardware链 | hardware | inspect | 支持调查/检查，不自动断言停机净收益 |
| 明确阵列/用户工作负载根因解释本次失败 | user_code | no_drain | 只否定该证据支持的硬件理由 |
| 有可复算暴露/工作负载差异，未证实硬件原因 | workload_mix | no_drain | 展示分母，不把计数当可靠性 |
| 空链、截断、单用户、缺对照、相互矛盾 | cannot_determine | cannot_determine | 记录需要补充的证据 |
| synthetic volume链 | cannot_determine | no_drain | 仅在独立合成演示中解释共同依赖；不可作为真实硬件结论 |

整体 verdict 默认 revise：把“按count直接drain”改为“按证据诊断”。只有充分限定范围才可reject对应建议理由；无足够证据则cannot_determine。accept表示接受建议中有证据的诊断方向，summary必须说明不是自动批准停机。

整体 evidence_origin 根据所引用记录分类为real_telemetry/synthetic_incident/mixed。研究到的synthetic字段以metadata.synthetic为准，不按目录名猜测。

测试案例必须手写虚构：两节点同一array根因、一个hardware对照、一条空链、一页截断、合成volume、所有calls失败。至少以下断言：

```python
def test_empty_chain_is_not_a_healthy_verdict():
    node = decide_node(
        node_name="fixture-node", resource_id="fixture-resource",
        findings=[], causal_results=[{"findings": [], "message": "No causal chain"}],
        reported_findings=1, returned_findings=1, truncated=False,
        scope_description="fixture episode", corroboration=None,
    )
    assert node.cause == "cannot_determine"
    assert node.verdict == "cannot_determine"
```

`decide_node` 是 investigation.py 内需实现的纯函数，参数及返回NodeAudit按本例定义；corroboration为本地查询结果dict或None。它必须可单测且不隐式访问网络。更详细的证据存于reasoning与引用calls，不扩展契约字段。

Run: `make test-api TEST_ARGS='track-2/tests/test_investigation.py -q'`。Expected：不同归因路径、预算计数、空链和分页局限都通过。

## Task M2.3：缓存、启动集成与真实审计

**Files:** Create `track-2/decision/audit_storage.py`, `track-2/tests/test_audit_storage.py`；向协调者提供bootstrap/cli接线建议，不自行编辑。

- [ ] 使用临时文件写完整JSON，flush后 `os.replace` 原子替换；中途取消不留半个合法结果。
- [ ] 写外层 `{"schema_version":"1.0.0","analysis_version":"track2-decision-v1","dataset_id":...,"investigation":...}`，load时全量验证；不兼容或损坏缓存返回None并日志说明。
- [ ] 使用数据集目录内`.audit.lock`文件的非阻塞flock，避免startup和手工audit同时写。锁由当前进程持有，退出自动释放，不凭文件存在判断永久锁定。
- [ ] 已录制调用发生错误时可返回partial；health/握手失败为failed；pagination截断或预算终止必须partial。completed仅代表声明的有限调查全部完成，不代表扫完全部集群。
- [ ] Bootstrap在API lifespan中后台调度audit；不要阻塞health等待120秒。schema导出、纯单元测试、fixtures模式不启动此后台任务。
- [ ] `TRACK2_AUDIT_MODE=off`显示not_run。auto模式复用有效缓存，缺缓存触发运行；UI可手动刷新记录，没有自由聊天入口。
- [ ] `make audit` 显式调用CLI，CLI使用 asyncio.run(run_investigation(...))，打印状态/调用数/覆盖，返回退出码：completed=0；partial且所需调用已成功=0并打印限制；failed=1。
- [ ] 从真实数据运行一次；审核工具名、参数、原始响应、时间、dataset_id和normalization一致；不把单元测试虚构记录当这一步的证据。

Run: `make test-api TEST_ARGS='track-2/tests/test_audit_storage.py -q'`、`make audit`。Expected：文件cache稳定且有效；记录包含成功MCP调用。网络工具本地运行无LLM key依赖。

## 3. M2交接清单

- [ ] 单元测试实际通过，canonical模型不改。
- [ ] load_investigation对无缓存/坏缓存有确定行为。
- [ ] 至少一次真实health/rules/recommendations/findings/causal序列，含一个有链案例；若当前top节点没有链，在剩余预算内通过detector过滤选一个代表案例，并明确它不属于top5审计结论。
- [ ] 第三方工具失败只影响audit状态，基本evaluation仍可用。
- [ ] out中结果可被API/UI读取；没有真实payload进入git。
- [ ] 向协调者报告status、call数量、被审计节点数、是否截断、真实/合成来源、文件路径、全部测试命令及退出码。

交接失败示例：只写了HTTP客户端；返回硬编码“已验证”；为了看起来完整忽略truncated；用空causal断言healthy；把固定0.58当误判概率。任何一项出现都不得通过G2-M。
