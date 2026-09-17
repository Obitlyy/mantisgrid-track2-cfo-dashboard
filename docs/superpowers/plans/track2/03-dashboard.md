# Track 2 Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 本文仅规划实现；不得将示例代码或预期结果当成已运行证据。

**Goal:** 构建英文 CFO 三卡页面，先贯通 CPU 迁移，再加入 idle 回收、组合去重与真实 MCP 调查记录。

**Architecture:** React 消费一次 `Evaluation` 原子展示支出、行动和风险；业务金额、候选、归属、排序由 decision 层提供。证据请求复用已应用的 `EvaluationRequest`，明细锁定 `dataset_id`；浏览器仅格式化数值。

**Tech Stack:** React、TypeScript、Vite、Vitest、Testing Library、MSW、Playwright、Nginx；沿用 F1 创建的 package/lock，新增依赖由前端提出并由协调者解析落锁。

**Spec:** [开发规格](../../specs/2026-09-17-track2-development-spec.md)、[统一契约](../../specs/2026-09-17-track2-contracts.md)、[执行总计划](../2026-09-17-track2-development-plan.md)。字段与公式以统一契约为准。

## 全局约束与所有权

- 工作根固定 `/Users/yiyangluo/Desktop/hackathon-2026-official-t1`；本计划执行前检查 `git status --short`，保留其他所有者改动。
- 仅英文 UI；全部 USD 是参考价格金额。`cash_savings_usd=null` 显示 `Unknown — no billing evidence`；不得使用 `|| 0` 消除未知。
- 全样本固定窗口；显示 `Historical sample` 和 `Calendar dates mapped from source offsets`，不增加日期筛选或下一季度预测。
- `schema_version="1.0.0"`、`analysis_version="track2-decision-v1"`；行动只有 `cpu_migration`、`idle_session_reclaim`。
- 仅 `/v1/decision`；HTTP 相对路径，`VITE_API_BASE_URL` 默认空字符串。Nginx 在容器 `:3000` 代理 `/v1/` 到 `api:8000`。
- `VITE_USE_FIXTURES=false` 为默认；fixture 模式仅用于本地开发/测试，并始终显示 `Fixture data — not real findings`。生产 API 失败不能切换假数据。
- 不要求 LLM key；所有资产、字体与浏览器请求在本机。页面按钮仅浏览、重算、下载，不运行调度操作。
- F1 所有者创建初始 `package.json`、锁文件、Pydantic/schema/fixtures 与生成类型；F1 门禁后前端接管 dashboard/src（不含generated）、样式与UI测试。依赖锁、构建/代理配置、Dockerfiles仍由协调者单写。
- `src/api/contracts.generated.ts` 只能经根级 `make contracts` 修改；禁止手写网络类型、编辑共享 fixture 或私自更名字段。需要契约变更先通知协调者。
- 根 Makefile、Compose、共享 Python/schema/fixtures 属于协调者或对应模块。前端提供 package scripts 与配置建议，由协调者落盘并接入 `make test-ui`、`make test-e2e`。
- 本文的 UI 数字来自手写测试 fixture，不是实际发现；真实截图、原始响应、测试 trace 只写忽略目录 `out/`。

## 文件地图与接口

以下路径均相对 `track-2/dashboard/`；组件只收 generated types 或本地展示状态，不定义另一套业务模型。

| 文件 | 单一职责与公开接口 |
|---|---|
| `src/api/contracts.generated.ts` | F1 生成；导出契约中同名模型，前端只读 |
| `src/api/client.ts` | `requestJson<T>(path, init): Promise<T>`；`evaluate(request, signal): Promise<Evaluation>`；规范错误适配 |
| `src/state/evaluationRunner.ts` | 下文 `createEvaluationRunner`；取消旧请求、忽略迟到结果、原子提交 |
| `src/state/useDecisionAnalysis.ts` | 加载 config，保存 draft/applied/evaluation、inspectedActionId 与展示状态；调用 runner |
| `src/App.tsx`、`src/main.tsx` | 注入 fixture 开关、加载页面、连接三个 tile 与抽屉 |
| `src/components/SampleContext.tsx` | `{ evaluation: Evaluation }`；窗口、价格版本、dataset/evaluation provenance |
| `src/components/ScenarioForm.tsx` | `{ draft: EvaluationRequest; onChange: (request: EvaluationRequest) => void; onApply: () => void; pending: boolean }` |
| `src/components/SpendTile.tsx` | `{ baseline: Baseline; onMethod: () => void }`；状态支出和代理 waterfall |
| `src/components/ActionTile.tsx` | `{ evaluation: Evaluation; selectedActionIds: ActionId[]; inspectedActionId: ActionId; onInspect: (id: ActionId) => void; onSelect: (ids: ActionId[]) => void; onEvidence: (id: ActionId) => void }` |
| `src/components/RiskTile.tsx` | `{ action: ActionEvaluation; scope: "standalone" | "marginal" }`；选择对应 risk，未知及试点条件 |
| `src/components/EstimateValue.tsx`、`StatusBanner.tsx` | 前者 `{ label: string; value: Estimate | null }`；后者可访问状态/错误提示 |
| `src/components/ClaimsExportButton.tsx` | `{ evaluation: Evaluation }`；本地team输入、服务端claims下载，不更改服务端文件 |
| `src/evidence/EvidenceDrawer.tsx` | `{ evaluation: Evaluation; actionId: ActionId; onClose: () => void }`；证据分页、scope、抽屉历史 |
| `src/evidence/JobDetailPanel.tsx`、`FindingPanel.tsx` | 分别 `{ detail: JobDetail }`、`{ detail: FindingDetail; onJob: (id: string) => void }` |
| `src/evidence/MethodPanel.tsx`、`McpAuditPanel.tsx` | 前者 `{ evaluation: Evaluation }`；后者 `{ datasetId: string; auditStatus: Evaluation["audit_status"] }` |
| `src/lib/format.ts` | `formatUsd(value: number)`、`formatHours(value: number)`；Intl 英文格式，仅最终显示舍入 |
| `src/mocks/handlers.ts`、`browser.ts` | 共享 JSON fixture 的 MSW 适配；`handlers` 导出为 HTTP handler 数组 |
| `src/test/setup.ts`、`src/__tests__/*.test.tsx` | jsdom/matcher 初始化、组件和竞态测试 |
| `e2e/decision-flow.spec.ts`、`playwright.config.ts` | 真实浏览器流程，产物写根 `out/ui/` |
| `src/styles.css` | 前端所有；响应式与可访问布局 |
| `vite.config.ts`、`Dockerfile`、`nginx.conf` | 协调者所有；前端提供同源开发代理、静态构建和容器配置建议 |

## U2：F1 后使用共享 fixture 独立交付 UI

**依赖/交付：** F1 的 `make check-contracts` 通过，十二个共享 fixture 与 generated types 已提交；U2 不等待真实分析/MCP。交付三个 tile、证据抽屉、明确假数据模式、单元测试及构建。

### U2.1 请求适配与本地测试入口

- [ ] 读取 shared fixture 和 generated types；确认 JSON import/`resolveJsonModule`、Vitest jsdom、MSW、Testing Library 已在锁文件内，没有另一套 fixture 格式。
- [ ] 在 `src/api/client.ts` 实现以下边界；`ApiError` 的 status/code/details 供页面区分错误。请求成功还要检查 schema_version 和当前预期 dataset；不认识版本时显示 `Unsupported response version` 并停止展示新结果。

```ts
import type { Evaluation, EvaluationRequest, ErrorResponse } from './contracts.generated';
export class ApiError extends Error {
  constructor(public status: number, public body: ErrorResponse) {
    super(body.error.message);
  }
}
export async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${import.meta.env.VITE_API_BASE_URL ?? ''}${path}`, init);
  if (!response.ok) throw new ApiError(response.status, await response.json());
  return response.json() as Promise<T>;
}
export function evaluate(request: EvaluationRequest, signal?: AbortSignal) {
  return requestJson<Evaluation>('/v1/decision/evaluate', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request), signal,
  });
}
```

- [ ] 对非 JSON 网关响应和 fetch 网络异常使用独立 `Service unavailable` 提示，不能把 JSON 解析失败解释为业务空结果。错误详情按 React 文本渲染，不使用 `dangerouslySetInnerHTML`。
- [ ] `src/mocks/handlers.ts` 从 `../../../contracts/fixtures/` 导入十二文件，含 `default-request.json`、两份evaluation及下表四份evidence。默认请求匹配 evaluation（CPU point15），双行动请求匹配 evaluation-both-actions（point17）；非支持参数返回明确 fixture 错误，禁止在 mock 中再实现财务公式。
- [ ] evidence handler同时匹配完整请求、action_id和scope，再原样返回明确对应的手写variant；禁止改写scope或evaluation_id，也不能只匹配选中行动而忽略价格/风险参数。未覆盖的开发情景显示 `Scenario unavailable in fixture mode`；真实U3支持全部合法scope。

| EvaluationRequest | action_id / scope | 共享文件 | contribution point合计 |
|---|---|---|---|
| 默认仅CPU | cpu_migration / marginal | `evidence-cpu-default.json` | 15 GPU-h |
| 默认仅CPU | idle_session_reclaim / standalone | `evidence-idle-standalone.json` | 5 GPU-h |
| 两行动、其余默认 | cpu_migration / marginal | `evidence-cpu.json` | 15 GPU-h |
| 两行动、其余默认 | idle_session_reclaim / marginal | `evidence-idle.json` | 2 GPU-h |

- [ ] 共享 dataset_id 保持一致；request/error fixture 无 meta，不强添契约外字段。investigation 的外层 meta.data_origin=test_fixture 表示测试来源，嵌套 evidence_origin 是虚构场景语义，并展示 limitations 内测试说明。
- [ ] `src/test/setup.ts` 定义 MSW server 生命周期如下；测试特例从此文件导入 server，用 MSW 的 `http`/`HttpResponse` 覆盖当前测试，不创建金融算法或另一套共享 fixture。

```ts
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { setupServer } from 'msw/node';
import { handlers } from '../mocks/handlers';
export const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => { cleanup(); server.resetHandlers(); });
afterAll(() => server.close());
```

- [ ] `main.tsx` 仅在 `import.meta.env.DEV && VITE_USE_FIXTURES === 'true'` 动态加载 MSW；正式构建遇到 fixture 标志为 true 直接失败。请求成功但 `meta.data_origin=test_fixture` 也必须显示 fixture 横幅。
- [ ] 开发 Vite 将 `/v1` 代理到 `http://localhost:8000`；root target 由协调者接线。先运行 `make test-ui` 的 client 测试得到缺实现失败，再完成适配与构建。

### U2.2 三卡布局和原子状态

- [ ] `useDecisionAnalysis` 定义本地状态 `phase: booting|ready|updating|error`、`draft: EvaluationRequest|null`、`evaluation: Evaluation|null`、`error: Error|null`；`applied` 始终取 `evaluation.request`，不另维护易漂移副本。
- [ ] GET config 后 clone `default_request` 为 draft，POST evaluate；首屏成功前显示 skeleton。默认 inspected 为 `cpu_migration`，selected 来自 config；rank 按响应展示，不强制 CPU 永远排名第一。
- [ ] inspectedActionId 与 draft.selected_action_ids 分离；点击行动只换风险/证据，勾选改变 draft，按 `Apply scenario` 发送整份请求。未选择行动可继续查看 standalone；禁止请求其 marginal evidence。
- [ ] ActionTile.selectedActionIds 取 draft，marginal值/风险资格取已应用的 evaluation.portfolio.selected_action_ids；草稿不同显示 `Unapplied changes`，避免尚未提交的checkbox改变已应用金额语义。
- [ ] `ScenarioForm` 展示 GPU 参考单价及 CPU 参考单价（可留未知）；高级区输入所有 Bounds 的 low/point/high。必填 f，optional r/c/d 提供 `Unknown` 开关；切已知后需填齐三值，不能自动默认为零。
- [ ] 本地检查数值有限、非负、low≤point≤high、f/r≤1、价格/c/d≤1000000；允许价格恰为0。发送 JSON number/null，清空字段不转成0；422 仍显示服务端校验原因。
- [ ] `evaluationRunner.ts` 使用以下实现，hook publish 时一次替换 Evaluation，保持三卡同一 evaluation_id；卸载调用 dispose。更新时旧卡保留且标记 `Previous scenario — updating`，当前草稿不混入旧金额。

```ts
import type { Evaluation, EvaluationRequest } from '../api/contracts.generated';
export function createEvaluationRunner(
  run: (request: EvaluationRequest, signal: AbortSignal) => Promise<Evaluation>,
  publish: (result: Evaluation) => void,
) {
  let sequence = 0;
  let controller: AbortController | undefined;
  return {
    async submit(request: EvaluationRequest) {
      const current = ++sequence;
      controller?.abort();
      controller = new AbortController();
      try {
        const result = await run(structuredClone(request), controller.signal);
        if (current !== sequence) return false;
        publish(result);
        return true;
      } catch (error) {
        if (current !== sequence || (error instanceof DOMException && error.name === 'AbortError')) return false;
        throw error;
      }
    },
    dispose() { sequence++; controller?.abort(); },
  };
}
```

- [ ] hook 只有 runner 返回 true 或最新请求抛错才结束 updating；迟到 false 不修改 phase/error。成功换 evaluation_id 时关闭旧抽屉并清除证据缓存；同 evaluation_id 的 audit 更新不误清除卡片。
- [ ] 首次加载失败显示可重试错误页面；更新失败保留旧 Evaluation并标记 `Previous scenario — update failed`，Retry提交当前draft。证据加载使用独立序号/AbortController，关闭抽屉或换dataset时废弃迟到detail结果。
- [ ] Tile 1 标题 `Where the money goes`：total measured GPU-hours/reference USD、全部 outcome rows（含 CANCELLED/unknown/0）；waterfall 标记 proxy，83% 不命名为 waste/recoverable。
- [ ] Tile 2 标题 `Where to cut`：action.title/action/owner_role/rank/effort、standalone 区间、当前组合 marginal、重叠数量用 jobs 表述、ranking_basis、portfolio 合计。责任角色不虚构已指派姓名。
- [ ] Tile 3 标题 `If this decision is wrong`：所看行动名及 scope、rerun GPU-hours/reference USD、CPU core-hours/cost、added job-hours、unknowns、success/stop/rollback。独立风险与 marginal 风险切换必须明示。
- [ ] 所有 Estimate 显示 low—high、point、`Scenario range` 和 basis；confidence=null 不转为百分比。Idle CPU 零值 basis 表示 `Not applicable`，CPU 未知成本仍显示 Unknown。
- [ ] 折叠区展示 `Gap to 20% of sample GPU-hours` 与 `Not a next-quarter budget commitment`；不自行计算 gap、相加 standalone 或从 reference savings 减成本生成现金收益。
- [ ] 1280px 三卡同排，窄屏按支出→行动→风险堆叠；所有按钮有英文 accessible name，状态不只靠颜色，数值不截断。表格可横向滚动并保留表头。
- [ ] U2即实现EvidenceDrawer、FindingPanel、JobDetailPanel和McpAuditPanel的展示及导航：通过同一HTTP client读取匹配fixture，显示scope/原因/原始逐卡字段、Back/Close和审计工具记录；I3再验证真实响应。detail handler核对URL里的真实fixture ID，不对任意ID返回同一job/finding。

### U2.3 组件与竞态测试

- [ ] 创建 `src/__tests__/risk.test.tsx`，先运行得到缺组件失败；实现后断言 Unknown 与零值区分、low/point/high、basis 和 scope。基础示例直接使用已验证共享 fixture：

```tsx
import { render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';
import fixture from '../../../contracts/fixtures/evaluation.json';
import type { Evaluation } from '../api/contracts.generated';
import { RiskTile } from '../components/RiskTile';
test('CPU cash savings remain unknown', () => {
  const evaluation = fixture as Evaluation;
  const action = evaluation.actions.find(a => a.action_id === 'cpu_migration');
  if (!action) throw new Error('Shared fixture must include CPU action');
  render(<RiskTile action={action} scope="standalone" />);
  expect(screen.getByText('Unknown — no billing evidence')).toBeVisible();
  expect(screen.queryByText('Verified savings')).not.toBeInTheDocument();
});
```

- [ ] 创建 `src/__tests__/evaluationRunner.test.ts`；下面测试刻意让 mock 不遵守 abort，确保仅 AbortController 不足时仍防住竞态。

```ts
import { expect, test, vi } from 'vitest';
import response from '../../../contracts/fixtures/evaluation.json';
import bothResponse from '../../../contracts/fixtures/evaluation-both-actions.json';
import type { Evaluation } from '../api/contracts.generated';
import { createEvaluationRunner } from '../state/evaluationRunner';
test('late response cannot replace the latest applied scenario', async () => {
  let resolveFirst!: (value: Evaluation) => void;
  let resolveSecond!: (value: Evaluation) => void;
  const run = vi.fn()
    .mockImplementationOnce(() => new Promise<Evaluation>(resolve => { resolveFirst = resolve; }))
    .mockImplementationOnce(() => new Promise<Evaluation>(resolve => { resolveSecond = resolve; }));
  const publish = vi.fn();
  const runner = createEvaluationRunner(run, publish);
  const oldResult = structuredClone(response) as Evaluation;
  const newResult = structuredClone(bothResponse) as Evaluation;
  const first = runner.submit(oldResult.request);
  const second = runner.submit(newResult.request);
  resolveSecond(newResult); await second;
  resolveFirst(oldResult); await first;
  expect(publish).toHaveBeenCalledTimes(1);
  expect(publish).toHaveBeenCalledWith(newResult);
});
```

- [ ] 其余测试覆盖选/看分离、空组合、零价、未填 optional、逆序 Bounds、503、无候选、unknown terminal、synthetic finding、长 ID 字符串、键盘 focus；金额与 percent 只断言格式，不复制后端公式。
- [ ] 测试default请求的CPU evidence scope=marginal、idle evidence scope=standalone，二者evaluation_id等于evaluation.json；双行动两页均等于evaluation-both-actions.json。只读共享文件，不能为使测试通过重写ID或scope。
- [ ] 运行 `make check-contracts`、`make test-ui`、`npm --prefix track-2/dashboard run build`；成功后记录结果。U2 仅提交自己所有的src/样式/测试；generated经 `make contracts`，package/config/Docker差异交由协调者落盘。

## I3 联调支持与 U3：真实贯通、Idle扩展和 MCP

**依赖/交付：** A3 提供真实 config/evaluate/evidence/raw detail；M2 提供 investigation。前端先支持协调者完成I3真实CPU路径；I3通过后执行U3的idle/MCP扩展。审计不可用不阻塞I3三卡，但最终U3门禁要求M2真实协议记录成功。

### I3 前端接线：CPU 证据和本机运行

- [ ] `EvidenceDrawer` 以已应用 evaluation.request POST `/v1/decision/actions/cpu_migration/evidence?scope=marginal&offset=0&limit=50`，禁止使用尚未应用的draft。已应用组合中的行动默认marginal，未选中行动默认standalone；请求marginal前确认行动已选中。
- [ ] 返回的 dataset_id/evaluation_id 与卡片一致才渲染；页内显示 included/excluded/overlap_assigned_elsewhere、原因、原始 measured/capped/candidate/contribution，不把行数当 finding 数。
- [ ] 下一页只使用服务端 next_offset，分页结果按返回顺序展示；不可对数字字符串 ID 作字典序排序。失败保留当前页并提供 Retry；0 rows/next_offset=null 明确 `No matching jobs`。
- [ ] 点击 finding GET `/v1/decision/findings/{finding_id}`；点击 job GET `/v1/decision/jobs/{job_id}`。路径 ID 用 encodeURIComponent；查询由 `new URLSearchParams({dataset_id: evaluation.meta.dataset_id})` 生成且必填，details 的 evaluation_id=null 合法。
- [ ] `FindingPanel` 展示 detector、impact_kind/scope、origin、method、关联资源和 job_ids；reported impact 标记为 reported，不能作为节省。causal_status=no_chain 显示 `No causal chain available`，不是失败。
- [ ] `JobDetailPanel` 展示 outcome、attempts、nodefail_nodes、offset 时间和全量 gpus；逐卡 node/gpu_id、raw duration、measured/capped hours、quality_flags 分列。禁止拿 primary_node 代替全部机器。
- [ ] 保留契约排除码并提供英文解释；`DURATION_CAPPED` 是调整警告，不是排除。`OVERLAP_ASSIGNED_TO_CPU_MIGRATION` 解释重复归属；`UNSAFE_SOURCE_IDENTIFIER` 对应 nullable ID显示 Unknown。一个job可有多条排除原因，不把reason计数相加当distinct jobs。
- [ ] `MethodPanel` 展示后端 basis/caveats、两种小时口径、固定 CPU→idle 归属、4h idle 门槛与 excluded 原因；说明没有逐时 idle tail、风险输入是情景假设。
- [ ] drawer 用 dialog/aria-modal；打开聚焦标题，Tab 不逃出，Escape/Close 关闭并恢复触发按钮 focus；内部 Back 恢复前一证据页，不能重新分析或丢失 action。
- [ ] 409 DATASET_MISMATCH 清除证据并显示 `Dataset changed — reload analysis`；404 明确 missing ID；422 ACTION_NOT_SELECTED 切 standalone 并解释；503 DATA_INVALID 显示数据错误，禁止用0或 fixture替代。
- [ ] 向协调者提供以下Nginx配置，保留路径前缀；Docker多阶段构建使用 `npm ci`。协调者修改构建文件并在根Compose挂dashboard:3000，前端不改共享配置或另建Compose文件。

```nginx
server {
  listen 3000;
  root /usr/share/nginx/html;
  location /v1/ { proxy_pass http://api:8000; }
  location / { try_files $uri $uri/ /index.html; }
}
```

- [ ] 增加服务端 claims 下载：要求非空 team，POST `/v1/decision/claims` 的 `{team, evaluation_request: evaluation.request}`；外层meta与analysis_provenance必须匹配当前dataset/evaluation。仅下载 ClaimsResponse.claims，经 Blob/object URL 导出并 revoke，不在客户端计算/舍入 claims。
- [ ] 配置 Playwright `baseURL=http://localhost:3000`，真实模式不启动 MSW；CPU 从金额到 finding/job/GPU 完成一条路径。先验收 CPU 真实金额与下载claims同 evaluation_id，再执行下一小节；开发测试团队名不得进入最终提交文件。

### U3.1 Idle、组合与 MCP 可审计记录

- [ ] 加入 idle 会话行动与证据 route（action_id=`idle_session_reclaim`）；显示固定 3.5h 提醒+0.5h 宽限的试点说明，不增加未入契约的 grace/timeout 输入。
- [ ] 两项同时选择后完全使用 portfolio 和 marginal 响应；手工 fixture 门禁是组合 point=17 GPU-h/$42.50、idle marginal point=2，不是 standalone point 之和20。真实数据不得硬编码这些数字。
- [ ] 查看未选中行动仍显示 standalone；portfolio 空集合展示0容量/成本且现金未知。overlap 被分配给 CPU 的证据行保留并显示原因。
- [ ] `McpAuditPanel` GET `/v1/decision/investigations/node_recommendation_audit` 并携带同样的必填 dataset_id 查询；状态 not_run/running/completed/partial/failed 分别明确显示，不因 HTTP200 就标为 verified。
- [ ] 展示 verdict、summary、limitations、finding_ids、evidence_origin；按 sequence 展开每次 tool_name、arguments、时间、duration_ms、status、标准化 result/error。结果用 `<pre>` 文本，ID 保持字符串。
- [ ] 展示 `nodes: NodeAudit[]` 的 node_name、cause、verdict、scope_description、reported/returned_findings、truncated、reasoning及finding_ids。截断显式警告，不渲染为完整调查；cannot_determine保留为正式结果。
- [ ] `nominal_drain_gpu_hours_24h` 标题为 `Nominal capacity at stake over 24 hours`，说明是名义容量、非实测损失或现金金额，不并入CPU/idle收益或风险合计。
- [ ] `no_chain` 结果与 timeout/error 区分；synthetic/mixed origin 显示合成情景标签。model_used=null且已有tool_calls时显示 `Deterministic MCP investigation`，not_run显示 `Investigation not run`；token_usage=null 不猜token数或隐藏为0。
- [ ] 审计窗口独立加载/失败，可手动 `Refresh investigation`；GET 返回状态直接更新审计面板，不等待 evaluate产生新ID。audit_status不参与evaluation_id，旧卡中的状态可显示读取时间以防混淆；不引入用户发起后台任务或聊天。
- [ ] 对I3已实现的claims下载增加双行动回归；确认来自当前组合的marginal总和，不能退回standalone相加。

### U3.2 真实浏览器门禁与交付

- [ ] `e2e/decision-flow.spec.ts` 断言 heading 三卡、CPU inspected 默认值、打开证据、选 finding/job、GPU 表、返回/关闭、改价 Apply 后三卡同步、idle inspected 风险变更、两项去重和 audit 展开；测试用响应字段/当前数据，不锁定真实样本金额。
- [ ] 为 ActionTile 证据按钮设置 `data-testid="evidence-" + action_id`；证据行设置 `data-eligibility`，按钮名 `View job {job_id}`；GPU表 accessible name=`Physical GPU records`。以下真实流程测试先跑失败，再贯通页面；该路径不依赖固定真实job ID。

```ts
import { expect, test } from '@playwright/test';
test('CPU recommendation reaches physical GPU evidence', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Where the money goes' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Where to cut' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'If this decision is wrong' })).toBeVisible();
  await page.getByTestId('evidence-cpu_migration').click();
  const dialog = page.getByRole('dialog');
  await dialog.locator('[data-eligibility="included"]').first()
    .getByRole('button', { name: /^View job / }).click();
  await expect(dialog.getByRole('table', { name: 'Physical GPU records' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByTestId('evidence-cpu_migration')).toBeFocused();
});
```

- [ ] 在浏览器监听 `page.on('request', ...)` 收集 hostname，断言全部 localhost/127.0.0.1；移除 LLM 环境变量后重启仍可操作。使用 390×844 和1280×900两种 viewport，截图与 trace 写 `out/ui/`。
- [ ] `make test-ui` 包含 unit/component+typecheck；`make test-e2e` 用 Playwright 指向已启动真实服务。两目标脚本和根接线由前端与协调者核对，不能以只有 HTTP200 的 smoke 代替交互测试。
- [ ] 运行 `make check-contracts`、`make test-ui`、`make test-e2e`；确认服务端没有 NaN/Infinity、source IDs未损失精度、相同 request的 evidence evaluation_id一致。发现契约错误先反馈，不自行加字段。
- [ ] 交付记录列出：通过命令、两种 viewport、真实 CPU/idle路径、MCP completed或有明确预算/截断说明的partial及必需调用真实成功记录、未知风险仍可见、生产无 fixture、claims provenance一致；failed/not_run不能通过，实际失败则保留未勾复选框。
- [ ] 最终由协调者在干净检出执行 plain `docker compose up` 验证 :3000；前端提交限自身文件，并提供英文四分钟演示路径：spend→CPU pilot→cost if wrong→raw evidence→idle overlap→MCP judgment correction。

## 并行门禁与回归边界

| 门禁 | 必须证据 | 可继续任务 |
|---|---|---|
| F1→U2 | generated types与十二个手写fixture校验通过；接口版本冻结 | 纯 UI/fixture 与分析/MCP并行 |
| A3+U2→I3 | 真实 POST evaluate/evidence及GET job/finding按契约工作 | 协调者CPU集成，前端支持 |
| I3→U3 Idle | CPU三卡金额/风险/证据与下载claims同evaluation_id | 第二行动与组合去重 |
| M2→U3 audit | 真实 MCP Client 调用记录可读取且dataset_id匹配 | 工具记录面板与最终审计验收 |
| U3→发布 | UI/e2e通过、真实双行动/审计可用、无假数据降级 | 干净Compose与提交材料验证 |

共享契约改动需要协调者更新版本、Pydantic/schema/fixtures，前端运行 `make contracts` 后复测受影响路径；不得为满足当前页面硬编码省略字段、重排归属或更改后端风险定义。
