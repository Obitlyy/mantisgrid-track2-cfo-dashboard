# Track 2 联调、验证与提交实施计划

> **For agentic workers:** 实施时使用 superpowers:executing-plans 或 superpowers:subagent-driven-development。协调者负责共享文件；依赖通过后再进入相应任务。仅在实际运行成功后勾选。

**Goal:** 把独立模块汇合成可复算、可交付的英文应用，并在干净检出中复现评委流程。

**Architecture:** 同一 decision Evaluation 驱动页面与claims；单 API进程、静态前端同源代理，真实数据与本地audit缓存分别挂载。根Compose默认只启动api和dashboard，notebook/tools按profile使用。

**Tech Stack:** 官方 Python锁加扩展锁、Docker Compose、pytest、Vitest/Testing Library、Playwright、官方claims验证脚本。

**Spec:** [开发规格](../../specs/2026-09-17-track2-development-spec.md)、[统一契约](../../specs/2026-09-17-track2-contracts.md)、[总计划](../2026-09-17-track2-development-plan.md)。

## Global Constraints

- claims必须引用与页面相同dataset/evaluation/request；不能手抄金额。
- 新增路由不改变官方API和MCP工具模型；import用于schema生成时无数据读取/网络副作用。
- 不公开数据、原始工具响应、截图中的完整行级明细或密钥；测试输出存忽略目录out。
- 不为修复警告发明置信度；实际团队名由用户提供，开发占位不能提交。
- 发布指这里的本地可交付验证，不包含未经请求的推送、公开仓库创建或表单提交。

## 1. 运行命令规范

所有命令从仓库根执行。F1创建targets，后续任务完成对应实现。脚本内部用argv数组传递参数，不把team/路径拼成shell代码。

| 命令 | 固定行为 |
|---|---|
| `make reuse-data` | 已下载数据迁移/复制到根；目标冲突则停止，保留源 |
| `make download-data` | 缺 raw 时由官方 prep 工具容器运行标准库安全下载脚本；不依赖宿主 Python |
| `make prep` | 官方prep，在根data写两表 |
| `make generate` | 官方Linux二进制，在根data写三文件 |
| `make check-data` | 官方值级检查，期望清单使用只读可信副本 |
| `docker compose up --build` | 完整默认应用；后续plain up必须可用 |
| `make up` | `docker compose up --build`便捷别名 |
| `make notebook` | 显式notebook profile，不是看板启动前提 |
| `make mcp` | 锁定环境运行官方stdio server，根级数据路径正确 |
| `make contracts` / `make check-contracts` | 导出契约/比较生成物并校验fixtures |
| `make test-api TEST_ARGS='track-2/tests/test_portfolio.py -q'` | 在根`/workspace`运行指定pytest参数；不隐式加载官方数据 |
| `make test-ui` | dashboard内先TypeScript typecheck，再Vitest unit/component非watch；任一步失败则非零退出 |
| `make test-e2e` | 对运行的localhost:3000跑真实浏览器测试 |
| `make audit` | 显式真实MCP有界审计，复用/重建依契约 |
| `make export-claims TEAM='实际团队名' REQUEST=out/release-request.json` | 以所给request复算并输出根claims.json；REQUEST省略用规范默认 |
| `make validate CLAIMS=claims.json URL=http://localhost:3000` | 官方schema/结构/HTTP检查，加项目语义/同源结果检查 |

开发机器若docker不在PATH，可在当前shell设置 `export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"`，不修改用户全局shell配置。评委一命令启动不依赖此macOS路径。

CLI固定入口 `python -m decision.cli`，子命令为 `audit`、`export-claims`、`validate`。共享解析参数 `--data-dir`、`--output-dir` 默认来自RuntimePaths。export参数 `--team`、可选`--request`、`--output`；validate参数`--claims`、可选`--dashboard-url`。root Make不创建第二个CLI。

tools容器的`/workspace`挂载仓库用于运行官方validator及读取其相邻starter schema；代码可通过`PYTHONPATH=/workspace/track-2`导入。构建时也确保正式镜像包含`/app/starter/claims.schema.json`与`/app/contracts/`，不能仅有scripts缺schema。

网络规则：宿主URL `http://localhost:3000`/`127.0.0.1:3000` 用宿主curl先检查真实端口；容器内官方检查映射为`http://dashboard:3000`，打印原URL与实际检查URL。其他合法http(s) URL原样检查；拒绝非HTTP协议。URL若省略仅做文件检查并显示未查页面。不能在tools容器直接用localhost3000冒充宿主服务。

## Task I3.1：API与生命周期汇合

**依赖：** A3、U2；M2可尚未完成，暂时audit=not_run。

**Files:** Modify `track-2/decision/app.py`, `bootstrap.py`, `cli.py`, root `docker-compose.yml`；新增 `track-2/tests/test_release.py`。A3提供`decision.routes.router`，M2提供run/load_investigation；不能再创建decision/router.py。

- [ ] app导入官方FastAPI实例，include_router(decision.routes.router)，只注册一次。
- [ ] 在API lifespan加载snapshot并保存到app.state；异常保留not_ready状态/诊断，不返回伪造样本。官方/decision健康检查均配置进入Compose readiness。
- [ ] 非MCP准备失败不能抛出未处理异常使首页静默成功；`/v1/decision/health`必须503且给出not_ready，基础数据错误可在ErrorResponse路由展示。
- [ ] 在有M2时通过bootstrap在lifespan内后台启动一次asyncio任务，120秒总预算；shutdown取消并等待子进程清理。不要在模块import或schema生成时启动。
- [ ] 有有效缓存即load；off则not_run；运行中显示running；失败时decision仍ready但audit failed。load_investigation最新状态必须能被GET调查和新evaluate看到。
- [ ] app缓存Evaluation时不把audit_status冻结：数学结果缓存按evaluation_id，返回时注入最新audit_status。审计状态变化不改变evaluation_id。
- [ ] 新增路由的验证/异常包装只影响 `/v1/decision`；官方错误handler保留原格式。
- [ ] 缓存LRU上限64，线程并发请求不得修改共享DataFrame或上次返回对象。测试价格A→B→A结果一致。

示例接线约束：

```python
# routes.py由A3定义router；app.py由协调者完成一次接入。
from api.main import app
from decision.routes import router
app.include_router(router, prefix="/v1/decision")
```

router本身不重复声明prefix。实际lifespan代码须保存/调用官方已有生命周期（若无则保持空默认）；不能因为示例短而忽略资源清理。

Run: `make test-api TEST_ARGS='track-2/tests/test_routes.py track-2/tests/test_release.py -q'`。Expected：官方路径兼容、新路径全部匹配、加载失败503、audit不阻塞health、cache不串请求。

## Task I3.2：CPU真实纵向验收

**Files:** 配置根Compose、由前端owner配合真实URL；测试文件`track-2/dashboard/e2e/decision-flow.spec.ts`归前端owner，协调者执行并记录。

- [ ] `docker compose config --services`默认服务只有api/dashboard，tools/notebook不自动启动；dashboard构建不含data/ZIP。
- [ ] `docker compose up -d --build`；带总超时等待官方`/health`和新增`/v1/decision/health`就绪，再检查dashboard与代理。
- [ ] GET config、用其default_request POST evaluate；必须meta.data_origin=official_dataset。
- [ ] CPU卡价格/小时、条件/责任角色/试点、未知CPU成本、cash unknown均可见。
- [ ] EvidencePage使用同一request且scope=marginal，meta.evaluation_id匹配；遍历所有页以贡献point求和，核对该行动marginal point（绝对误差≤1e-6）。
- [ ] 至少点开一个finding、对应job、该job所有GPU行；详情dataset_id与卡相同，方法和截断读数明确。
- [ ] 以不同price重算：所有候选/小时相同，reference dollars按比例改变；页面没有不同evaluation_id混用。
- [ ] 使用同一已应用request POST `/v1/decision/claims`；断言外层meta与claims.analysis_provenance的dataset_id/evaluation_id均与页面一致，GPU/USD值等于build_claims的舍入输出。通过页面下载JSON并解析验证；测试team=`Integration Test Team`仅用于忽略目录内测试文件，不生成或提交最终根claims。
- [ ] 取消所有行动：组合0、风险0/不适用、cash unknown；仍可查看独立候选详情。

需要的只读HTTP冒烟脚本`track-2/scripts/smoke_decision.py`由协调者实现：使用stdlib urllib获取config/evaluate/evidence，并POST仅返回JSON的claims接口；assert官方origin和schema、分页sum与claims provenance/舍入一致；打印dataset_id/evaluation_id，不输出完整真实行、不写服务端文件。正式团队名、根文件导出与官方validator仍在R4验收。

Run: `python3 track-2/scripts/smoke_decision.py --url http://localhost:3000`。Expected：HTTP成功、ID一致、证据合计一致；不存在候选时明确报“无可演示候选”而不是编造行，回查真实筛选。

## Task U3/I3.3：双行动与MCP汇合

- [ ] 选中CPU+Idle后请求重算，组合point等于两行动marginal point之和；standalone point之和允许更大并解释overlap。
- [ ] 单独Idle时被CPU占用的任务重新进入Idle候选贡献；固定归属与rank排序互不影响。
- [ ] 改变risk输入但不改变recoverable_fraction时，收益不变、风险变化；值缺失时不能变$0。
- [ ] Inspect action与selected actions分离：查看未选中行动使用standalone；当前组合显示marginal。
- [ ] 调查GET展示真实tool call、归因理由、覆盖/截断、nominal capacity；manual refresh更新最新audit状态，不重新写算术结论。
- [ ] 模拟API断开显示错误/上一版本标记；不自动进入fixture模式。
- [ ] 页面英文、键盘操作和窄屏测试通过。

Run: `make test-ui`、`make test-e2e`、`make audit`。Expected：真实路径至少一次完整通过；MCP若partial需有明确truncation/预算原因及真实成功calls，不能是failed/not_run。

## Task R4.1：claims与语义验证

**Files:** 实现CLI接线；新增 `track-2/decision/validation.py`、`track-2/tests/test_validation.py`，根claims.json作为最终产物；不改官方validator。

新增内部函数 `validate_claims_semantics(claims: dict, evaluation: Evaluation) -> list[str]`：返回问题列表，空表示语义通过。导出时必须从当前Evaluation调用build_claims，CLI把JSON写临时文件并原子替换目标，禁止写到data官方目录。

- [ ] 确认team非空且不是开发占位；缺团队信息只阻塞最终导出，不能阻塞分析/UI开发。
- [ ] 从当前页面提交参数记录为忽略的`out/release-request.json`，导出的claims带完整analysis_provenance。
- [ ] 检查 low≤point≤high、所有数有限、GPU收益上限不超过所选候选与样本measured上限、USD按同一price和舍入规则一致。未舍入内部结果用1e-6浮点绝对容差；claims与重新build_claims的同舍入结果逐值比较，不用已舍入claims直接严格比较未舍入ceiling（可有半个最后小数位差异）。
- [ ] 验证claims evaluation_id/dataset_id是重新计算结果；拒绝把手改金额或旧数据claims当有效。
- [ ] interval_kind=scenario、basis说明假设，null confidence导出时省略；不为官方警告增加虚构incident_confidence。
- [ ] 对未调查的node_triage/hardware/incident等字段保持省略。MCP的bounded节点检查不能直接变全样本hardware失败计数。
- [ ] 官方validator实际schema和脚本都运行，追加项目语义验证。官方警告列出但区分warning/error；不得修改官方expected清单让数据通过。

测试代码样例：

```python
def test_rejects_claims_detached_from_evaluation():
    e = evaluate(golden_snapshot(), default_request())
    claims = build_claims(e, "Fixture Team")
    claims["recoverable_gpu_hours"]["point"] += 1
    problems = validate_claims_semantics(claims, e)
    assert any("recoverable_gpu_hours" in item for item in problems)
```

此处golden_snapshot/default_request来自tests/factories.py，其余函数来自canonical service/claims和本任务validation.py；不要另写不同fixture。

Run: `make export-claims TEAM='实际团队名' REQUEST=out/release-request.json`，`make validate CLAIMS=claims.json URL=http://localhost:3000`。Expected：schema、HTTP、语义均通过，已知“无顶层confidence”警告可解释。

## Task R4.2：英文提交说明和演示

**Files:** root README.md、REPORT.md、`docs/demo-script.md`。保留原Track1链接/贡献，不删除无关文档。

README固定内容：项目/track、三张卡说明、数据下载/生成/check-data根级命令、一命令启动、访问端口、可选notebook/MCP、依赖与本地模型不必需、数据许可/归属、AI模型和工具披露。

REPORT固定内容：

1. Executive decision：两候选行动及与20%目标的可比范围。
2. Data and scope：sample/window/physical grain/官方check-data；不是fleet全量。
3. Cost baseline：measured口径与SM代理，所有终态。
4. Actions and ownership：CPU/Idle具体动作、责任角色、筛选、证据。
5. Recovery and overlap：异常caps、requeue排除、独占归属、区间假设。
6. Cost of being wrong：CPU/重跑/延迟、未知信息、试点和回滚。
7. MCP audit：真实工具调用及与Layer B比较；coverage/合成标记。
8. Reproducibility：dataset_id、analysis_version、claims参数和校验命令。
9. Limitations：无账单兑现、无季度预测、无校准概率、无idle时间序列。
10. AI disclosure：实际使用的模型/框架/代理及生成范围，无法获取的token计数写未记录，不捏造。

四分钟演示分配：0:00–0:35支出与sample；0:35–1:25一个具体行动/角色；1:25–2:10误判情景/未知成本；2:10–3:05原始证据；3:05–3:40 MCP如何修正按count停机；3:40–4:00试点/回滚与目标差距。每段都对应应用真实可点击功能。

## Task R4.3：干净检出与最终检查

只在所需源码已被正确提交到本地开发分支之后执行；有未提交实现则clean clone不会包含，先完成正常review/commit。不要为了clean test合入无关改动。

示例临时目录命令（执行时先确认实际分支和路径）：

```bash
release_check_dir=$(mktemp -d /tmp/track2-release-check.XXXXXX)
git clone --no-hardlinks /Users/yiyangluo/Desktop/hackathon-2026-official-t1 "$release_check_dir/submission"
cd "$release_check_dir/submission"
# 按根 data/README.md 下载官方原始包并生成，禁止复制本机 out 缓存。
make download-data
make prep
make generate
make check-data
docker compose up
```

`make download-data`由F1定义为首用下载命令：已有四个非空普通raw文件时幂等跳过，缺数据时在官方prep工具容器内用stdlib urllib从官方URL下载；先zip完整性/路径检查，再安全解压。raw跳过不等于来源校验，派生文件仍须通过make check-data。它用于评委/clean clone重现，不意味着本次需要重下已有数据。

如果主开发实例仍占8000/3000，协调者先停止该实例，或使用明确独立project/测试端口配置；最终至少一次按默认3000验证。不要并行两个Compose争夺同一端口，或靠隐藏本机服务让clone测试通过。

- [ ] 确认只有一个有效docker-compose.yml；default服务不依赖手工run notebook或MCP。
- [ ] 不复制out、node_modules、本机venv；没有私有绝对路径、宿主API路径或秘密环境变量。
- [ ] 没有LLM key仍能看到真实数据；MCP独立真实启动/审计，cold cache测试一次。
- [ ] 重跑schema/语义/UI交互/证据合计验证，记录真实退出码。
- [ ] `git ls-files`无raw/prepped/synthetic/ZIP/out/.env；根claims/README/REPORT被跟踪。
- [ ] `git diff --check`无格式问题；README列出的命令可以按顺序执行。
- [ ] 保留验证结果到原工作目录out/release/，只在报告引用结果，不提交真实行级输出。

常见失败定位：schema missing→镜像没有starter；localhost失败→容器地址误用；官方store找错data→MGAI_DATA_DIR；claims不存在→gitignore；前端能开API404→代理/path双prefix；只在mock工作→fixture未关闭；日期像真实测量→映射标签缺失。

## 2. 发布门禁记录模板

```text
Commit: 实际被验证的本地提交SHA
Contract: 1.0.0
Analysis: track2-decision-v1
Dataset: 当次计算的完整dataset_id
Official check-data: 5/5，实际退出码
Contract/schema: 实际命令与退出码
Python/UI/browser tests: 实际用例数与退出码
Claims: evaluation_id、参数文件、schema/语义结果
MCP: 真实call数、status、覆盖/局限、缓存是否cold
Clean clone: 默认:3000、数据重新生成、是否需要额外手动命令
Remaining limitations: 明确列出未知/未调查项
```

全部通过后交接用户可启动入口、报告/claims、剩余局限。若公开发布/正式提交尚未获授权，交付本地可审查成果即可，不自行提交表单。
