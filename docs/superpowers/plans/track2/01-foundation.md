# Track 2 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 本文件只规划实现；当前交付不得安装依赖、启动服务、生成数据或修改应用代码。

**Goal:** 建立可复用根级数据、唯一启动入口和可机械验证的 Python/JSON/TypeScript 契约，交给分析、前端和 MCP 三个并行执行单元。

**Architecture:** 根级 Compose 运行 `api` 与 `dashboard`；`decision.app:app` 扩展官方 FastAPI，Nginx 在 `:3000` 同源代理 `/v1/`。官方 prep/generate 保持原镜像与算法；新 API 镜像增加 decision/MCP 依赖，所有进程读取同一根级数据。

**Tech Stack:** Python 3.12、官方锁定的 FastAPI/Pydantic/pandas/PyArrow、独立锁定的 FastMCP/pytest；React/TypeScript/Vite、Nginx、Docker Compose、uv、JSON Schema。

**Spec:** [开发规格](../../specs/2026-09-17-track2-development-spec.md)；[统一契约](../../specs/2026-09-17-track2-contracts.md)。字段、枚举、签名和公式只以统一契约为准。

## 全局约束与交接边界

- 工作根固定 `/Users/yiyangluo/Desktop/hackathon-2026-official-t1`；先核对当前目录与已有改动，不碰相邻工作树或 Track 1 业务代码。
- 固定 `schema_version="1.0.0"`、`analysis_version="track2-decision-v1"`、前缀 `/v1/decision`、行动 `cpu_migration` / `idle_session_reclaim`。
- 唯一类型源 `track-2/decision/contracts.py`；生成 schema/OpenAPI/TS，禁止前端手写网络类型。应用和 fixtures 的说明文字使用英文。
- F1 实现 `data.py`、`config.py`、`contracts.py`、`errors.py`、`tests/factories.py`；A2 消费这些共享文件，变更通过协调者。
- F1 建立 `app.py`、`cli.py`、`bootstrap.py` 接线骨架，后续只有协调者集成；`routes.py` 暴露 `router: APIRouter` 并在 F1 后交 A3。分析服务函数交 A2；`investigation.py` 骨架交 M2。
- 根 Compose/Make、所有锁文件、共享测试工厂、生成文件、dashboard package/config 归协调者；U2 只独立编辑前端业务源代码及其测试。
- Python 使用隔离 uv 环境，Node 依赖装在 dashboard 本地目录，禁止全局 pip/npm 安装；已有 Conda 或其他项目依赖不是本项目验证环境。
- 真实数据、MCP 原文和截图只在忽略目录；提交需要的 root `claims.json` 显式解除忽略。阶段门禁前不提交，不自动 merge/push。

本文件按交付职责分任务，执行依赖固定为：F1.1 只读盘点/忽略/复制脚本 → F1.2 锁与 runner → F1.5 模型定义 → F1.4 loader → F1.7 离线路由骨架 → F1.1 数据复制与 F1.3 Compose → F1.5 导出链与 F1.6 fixtures → 全部门禁。`check-contracts` 的全量 fixture 验证在 F1.6 文件齐全后执行；不能把导出链误设为依赖 API healthy 的在线请求。

## Task F1.1：记录起点并安全复用根级数据

**Files:** 创建 `data/README.md`、`data/checksums.txt`、`track-2/scripts/{reuse_data,download_data}.py`、`track-2/contracts/official-checksums.txt`；修改 `.gitignore`；测试 `track-2/tests/{test_data_reuse,test_download_data}.py`。

**Interfaces:** 输入既有 `track-2/data/{raw,prepped,synthetic}`；输出根 `data/` 同内容树。官方摘要、生成器、`prep_data.py` 不改动；官方五文件顺序沿用 `scripts/checksum_data.py.FILES`。

- [ ] 运行以下只读检查，记录当前分支、已有改动、Docker/uv 与实际数据位置；历史 5/5 通过不是当次证据。

```bash
cd /Users/yiyangluo/Desktop/hackathon-2026-official-t1
git status --short
git branch --show-current
/Applications/Docker.app/Contents/Resources/bin/docker compose version
uv --version
rg --files track-2/data data
unzip -t track-2/track-2-raw.zip
```

- [ ] 先修忽略规则：`/data/*` 后允许 `/data/README.md`、`/data/checksums.txt`；忽略 `**/track-2-raw.zip`、`out/`、`.env`、`node_modules/`、`dist/`、pytest/coverage 缓存；现有 `claims.json` 规则后加 `!/claims.json`。
- [ ] `reuse_data.py` 仅接收 `--source` / `--destination`：先列举允许的四 raw 文件及五派生文件，禁止 symlink/目录逃逸；同路径同内容跳过，任何既有不同内容先报冲突并退出，不覆盖、不删除源目录。缺失派生文件报告为需要官方生成，不能制造空文件。
- [ ] `download_data.py --destination` 仅用 urllib/zipfile/pathlib/tempfile 标准库，从 `https://mantisgrid-hackathon.s3.us-east-1.amazonaws.com/track-2-raw.zip` 下载到临时目录；现有四个非空普通 raw 文件齐全时跳过网络。检查 zip.testzip、四个精确顶层名字、非绝对/无`..`/非symlink，再解压至临时目录，完整预检目标冲突后复制；异常不留下半个可用 raw 数据集。不存在已公布 ZIP digest，不宣称完整性测试等于来源哈希校验。
- [ ] 用 `tmp_path` 写三个测试：空目标复制后 SHA-256 相同；第二次运行无改变；一个目标文件内容不同，运行非零且该文件及其他目标文件都未改变。实现先全量预检、后复制，防止半途才发现冲突。
- [ ] download 单测用内存构造四文件 ZIP 并替换 urllib transport：正常解包、二次零网络调用、损坏ZIP、`../`路径、symlink、目标内容冲突分别断言，无测试需要网络或官方raw内容。
- [ ] 将官方 manifest 原字节复制到根 `data/checksums.txt` 和 `track-2/contracts/official-checksums.txt`；后者是打包进镜像的校验依据，不能信任可写 data 挂载中的替换清单。
- [ ] 根数据说明写明 `make prep` → `make generate` → `make check-data`、四个 ZIP 顶层文件、下载来源、许可、不提交数据及已有数据复用命令。
- [ ] F1.2 的 runner 建好后执行，脚本必须保留原 `track-2/data/`：

```bash
uv run --isolated --no-project --python 3.12 --with-requirements track-2/requirements.dev.lock.txt python -m pytest track-2/tests/test_data_reuse.py track-2/tests/test_download_data.py -q
uv run --isolated --no-project --python 3.12 --with-requirements track-2/requirements.dev.lock.txt python track-2/scripts/reuse_data.py --source track-2/data --destination data
cmp track-2/data/checksums.txt data/checksums.txt
cmp track-2/data/checksums.txt track-2/contracts/official-checksums.txt
git check-ignore data/prepped/jobs.parquet track-2/track-2-raw.zip out/audit.json
git check-ignore claims.json
```

**验收:** 三个数据路径应被忽略，最后的 claims 检查应退出 1；五个真实文件需要在 F1.3 再做官方值级校验。不能用“复制成功”代替 checksum。

## Task F1.2：隔离依赖并建立可执行开发命令

**Files:** 创建 `track-2/requirements.{decision,dev}.in`、对应 `.lock.txt`、`track-2/dashboard/{package.json,package-lock.json,tsconfig.json,vite.config.ts,vitest.config.ts,playwright.config.ts,index.html}`、`track-2/dashboard/src/{main.tsx,App.tsx}`；创建根 `Makefile`、`.env.example`、`pytest.ini`。

**Interfaces:** 官方 `requirements.lock.txt` 为不可变约束；新依赖只从新增锁安装。根 target 名称固定为 `contracts`、`check-contracts`、`test-api`、`test-ui`、`test-e2e`、`audit`、`export-claims`、`validate`，以及 `download-data/reuse-data/prep/generate/check-data/up/down/notebook/mcp`。

- [ ] `requirements.decision.in` 包含 `-r requirements.lock.txt` 与 `fastmcp`；dev 输入包含 `-r requirements.decision.lock.txt`、`pytest`、`pytest-asyncio`。每个 direct 新包先解析兼容性，再把实际版本写入 `.in` 并重新锁定；禁止臆造未验证版本或更新官方 pin。

```bash
cd /Users/yiyangluo/Desktop/hackathon-2026-official-t1/track-2
uv pip compile requirements.decision.in --python-version 3.12 --output-file requirements.decision.lock.txt
uv pip compile requirements.dev.in --python-version 3.12 --output-file requirements.dev.lock.txt
uv run --isolated --no-project --python 3.12 --with-requirements requirements.dev.lock.txt python -c 'import fastapi, pydantic, pandas, pyarrow, fastmcp, pytest'
```

- [ ] dashboard 选择当前可用且满足 Vite engine 的 Node LTS，实际记录精确 Node 版本和镜像 digest；安装 `react`/`react-dom`、`vite`/`typescript`/`@vitejs/plugin-react`、`@types/react`/`@types/react-dom`、`vitest`/`jsdom`/`msw`/`@testing-library/react`/`@testing-library/jest-dom`/`@testing-library/user-event`、`@playwright/test`、`json-schema-to-typescript` 并锁定，`package.json` 使用精确版本，后续一律 `npm ci`。
- [ ] package scripts 为 `dev`、`build`、`typecheck`、`test`、`test:e2e`、`contracts`；build=`tsc --noEmit && vite build`，test 单次运行而非 watch。Playwright 使用 `http://localhost:3000`；Vite 同源 `/v1` 代理到 `http://localhost:8000`。
- [ ] 初始 `App.tsx` 只显示英文 `Decision dashboard is initializing.`，不显示 fixture 数字或“ready”；frontend 包和导出链可编译后再交 U2。
- [ ] `.env.example` 只列统一契约环境变量：两 DATA_DIR 解析到同一路径，OUTPUT_DIR 指向 `out`，AUDIT_MODE=auto，TEAM 留空并解释仅最终导出必需，两个 Vite 默认值按规格。
- [ ] Make 确定仓库绝对路径，不依赖调用者 cwd；`test-api` 使用 tools 容器、工作目录 `/workspace`、`PYTHONPATH=/workspace/track-2`，把 `TEST_ARGS` 的根级路径原样传给 pytest，禁止隐式裁掉 `track-2/`。可用 `DOCKER` 覆盖客户端路径，默认先 PATH 再已知 Docker Desktop 路径。
- [ ] 根 `pytest.ini` 固定 `pythonpath = track-2 track-2/tests`、`testpaths = track-2/tests`；注册 `real_data: explicitly enabled official-data integration tests` marker。共享导入固定 `from factories import golden_snapshot, default_request`，不依赖通用 `tests` 包名，避免第三方同名包。tools 从 `/workspace` 按 TEST_ARGS 根路径执行；子模块 helper 采用独有名字 `analysis_fixtures`。未显式提供数据目录的 real_data 测试在运行时skip，collection不读真实文件。
- [ ] `contracts/check-contracts` 使用本地锁定的 uv Python 与 Node 离线生成，既不启动 Compose 服务也不读取真实数据；所有 uv run 都显式 `--isolated --no-project --python 3.12`，避免已有 Conda 环境污染。`test-ui` 先运行typecheck，再运行Vitest unit/component非watch并透传 `UI_ARGS`；任一步失败即非零退出。`test-e2e` 透传 `E2E_ARGS`。未接通实现必须明确非零退出，禁止 `echo success`。
- [ ] `download-data` 通过官方 prep 工具容器运行 `python scripts/download_data.py --destination /app/data/raw`；`reuse-data` 调用复制脚本的 source=`track-2/data`、destination=`data`；`notebook` 调用 `docker compose --profile notebook up notebook`。源码现有raw齐全时不执行下载；clean clone可用这些同名目标。
- [ ] CLI 精确子命令为 `audit --data-dir --output-dir`、`export-claims --team --request --output`（request 可省略）、`validate --claims --dashboard-url`（dashboard-url 可省略）；Make 的 audit/export-claims/validate 调用它们，完整校验与根路径换算由发布计划接续。

**验收:** `npm --prefix track-2/dashboard ci`、`npm --prefix track-2/dashboard run build` 成功；官方 lock 的 `git diff` 为空；新增 lock 可在干净缓存安装。依赖冲突由协调者调整新增包，不能解锁官方版本。

## Task F1.3：迁移唯一 Compose 入口并保留官方准备链

**Files:** 创建根 `docker-compose.yml`、`.dockerignore`、`track-2/.dockerignore`、`track-2/decision/Dockerfile`、`track-2/dashboard/{Dockerfile,nginx.conf}`；旧 `track-2/docker-compose.yml` 重命名为 `.example`；修改 `track-2/Makefile` 为根命令转发；修改 `track-2/starter/Dockerfile` 使用官方 lock。

**Interfaces:** 只有两个默认长驻服务 `api`、`dashboard`。`prep/generate/tools` 在 tools profile；`notebook` 在 notebook profile。API 容器内代码 `/app/{api,decision,mcp_layer}`，数据 `/app/data:ro`、缓存 `/app/out:rw`。

- [ ] `prep/generate` build context=`./track-2`、dockerfile=`api/Dockerfile.local`、cwd=`/app`，原镜像和原命令不变；挂载根 `./data:/app/data`，scripts/bin 仍来自 `./track-2`。生成器按 Linux amd64/arm64 选择，保留复制 `/tmp/gen` 后执行的逻辑。
- [ ] `make check-data` 使用官方 checker，额外挂载可信 manifest 为 `/app/official-checksums.txt:ro`；命令固定 `python scripts/checksum_data.py --data /app/data --expect /app/official-checksums.txt`，绝不运行 `--write`。
- [ ] 新 `decision/Dockerfile` 安装新增 decision lock；复制 api、decision、mcp_layer、scripts、contracts 和 `starter/claims.schema.json`，不 COPY data。底层 Python 镜像使用本次已检查的 digest，架构声明必须覆盖实际部署机。
- [ ] Dockerfile 增加 tools build target 安装 dev lock；tools 服务挂载根源码到 `/workspace`、cwd `/workspace`、`PYTHONPATH=/workspace/track-2`。需要生成/导出的源码挂载可写，根 `data` 另以只读覆盖；真实缓存指向 `/app/out`，测试输出按 `out/tests/<task_id>/` 分离。
- [ ] API 唯一命令为 `uvicorn decision.app:app --host 0.0.0.0 --port 8000`，生产单进程、无 reload。bootstrap.py 只提供 lifespan helper，不是另一个启动入口。data 两环境变量均 `/app/data`，output `/app/out`；healthcheck 指向 `/v1/decision/health`。
- [ ] dashboard 采用 npm ci 的 builder 和精确镜像版本的 Nginx，内部 `listen 3000`、端口映射 `3000:3000`，供tools使用 `http://dashboard:3000`。`location /v1/` 代理保留完整 URI 到 `http://api:8000`；静态 `try_files $uri $uri/ /index.html`，API 错误不可被 SPA fallback 变成 200 HTML。
- [ ] dashboard 对 API 使用 `depends_on: {api: {condition: service_started}}`，可在 F1 渲染真实的 not_ready；API healthcheck 仍检查 decision health，最终发布必须另行等待官方与 decision 都 healthy。审计在 lifespan 后台执行，不能把120秒审计串行加到 health 等待或伪造 ready。
- [ ] notebook 使用 `127.0.0.1:8888:8888`、`MGAI_URL=http://api:8000`、`./track-2/starter:/work`；需要直接分析时附根 data 只读挂载。保留 `mgai_client.py` 路径，所有提交 notebook 清空 outputs/execution_count。
- [ ] 两级 `.dockerignore` 排除所有 data、ZIP、out、.git、.env、node_modules/dist；精确保留镜像需要的源码、locks、schema 与可信 manifest。
- [ ] 接线后执行以下命令，现有根数据通过则无需重跑 prep/generate；缺数据时按说明运行两个官方步骤再复查。

```bash
make check-data
/Applications/Docker.app/Contents/Resources/bin/docker compose config --quiet
/Applications/Docker.app/Contents/Resources/bin/docker compose config --services
rg --files --hidden -g docker-compose.yml -g '!node_modules' -g '!.git'
git diff -- track-2/api/Dockerfile.local track-2/scripts/prep_data.py track-2/scripts/checksum_data.py track-2/requirements.lock.txt
```

**验收:** 官方五个输出全部 `ok`；只存在根 exact `docker-compose.yml`；默认长驻服务为 api/dashboard；不可变官方文件 diff 为空。plain up 的真实页面成功留到集成门禁，F1 不提前宣称完成。

## Task F1.4：实现共享路径、错误与只读快照

**Files:** 创建 `track-2/decision/{__init__,config,errors,data}.py`；仅路径适配 `track-2/api/data_loader.py`；测试 `track-2/tests/{test_config,test_data,test_official_compatibility}.py`。

**Interfaces:** `resolve_paths() -> RuntimePaths`；`load_snapshot(data_dir: Path) -> DataSnapshot`；`DecisionError(code, message, details, http_status)`，结构与统一契约 §8 一致。

- [ ] `RuntimePaths` frozen dataclass；本地默认 repo/data、repo/out，容器 env 显式覆盖；`.expanduser().resolve()` 后两个 DATA_DIR 必须相同。冲突拒绝启动并返回可读错误，不自动复制或生成。
- [ ] 官方 loader 只增加 `os.environ.get("MGAI_DATA_DIR")` 路径优先级，缺省仍原 ROOT/data；不改变 Store 行筛选、聚合、routes 或 models。用两次独立子进程验证默认路径与 env 路径，避免模块 import cache 污染。
- [ ] `DataSnapshot` 完整包含 dataset_id/jobs/gpus/resources/edges/findings/sample_window/data_origin；读取全部五文件，禁止借用官方 Store 充当逐卡数据源。DataFrame 所有权只读约定；消费者临时加列必须 copy。
- [ ] loader 缺文件抛 503 `DATA_NOT_READY`；使用官方 digest 函数逐文件比较可信 manifest，差异抛 503 `DATA_INVALID`。检查 jobs/resources/findings 主键唯一、GPU 物理 key `(Node,gpu_id,id_job)` 唯一、必需列、jobs 基线利用率有限，异常 details 仅字段/计数，不倾倒真实数据。
- [ ] 保留未知终态和所有 measured 行；逐卡缺 join、requeue、异常 duration 的候选处理交 A2，不在此删除 job。无法安全恢复的 job 主键使门禁失败，nullable user/array 的不安全 float ID 保留未知标记。`sample_window` 取有效 submit min/end max，epoch 从 `api.main.DEFAULT_PRICE_BOOK.epoch_offset` 获取，UTC 字符串明确人为映射。
- [ ] dataset_id 对五文件实际 digest 按官方顺序构造 `relative_path + " " + digest + "\n"` 后 SHA-256；禁止只 hash 清单。fixture 由共享工厂直接构造 snapshot，不能给真实 loader 增加跳过校验的生产开关。
- [ ] 单测覆盖路径不同拒绝、缺文件、摘要不符、主键重复、缺基线利用率、保留 UNKNOWN、映射日期、稳定 digest；数据内容错误用测试注入 reader/digest，不能改官方期望摘要。

```bash
make test-api TEST_ARGS='track-2/tests/test_config.py track-2/tests/test_data.py track-2/tests/test_official_compatibility.py -q'
make mcp
```

**验收:** MCP 从 `track-2/` 启动但 `MGAI_DATA_DIR` 为根 data 绝对路径；保持 stdio，不打印普通日志到 stdout。此命令能启动服务器仅证明路径/依赖，不等同完成 MCP 协议审计。

## Task F1.5：冻结完整请求/响应及可验证生成链

**Files:** 创建 `track-2/decision/contracts.py`、`track-2/scripts/{export_contracts,check_contracts}.py`、`track-2/dashboard/scripts/generate-contracts.mjs`、生成 `track-2/contracts/{decision.schema,openapi}.json`、`track-2/dashboard/src/api/contracts.generated.ts`；测试 `track-2/tests/test_contracts.py`。

**Interfaces:** 契约 §2–8 的全部模型与精确字段；非业务实现。export 脚本注册全部模型为 `$defs` 并构造可导出的 bundle；schema draft 与 jsonschema validator 一致。

- [ ] 按契约逐模型写定义；extra forbid、禁止 NaN/Infinity、数字拒绝字符串及 bool，nullable 响应字段完整输出。实现 Bounds 顺序和参数上限、行动去重、空白 team、只允许十进制字符串的作业 ID。
- [ ] 先写以下有意义的拒绝测试并运行失败，再实现约束；另外断言 0 价格与空 selected list 合法，不把合法整数 JSON number 拒掉。

```python
@pytest.mark.parametrize("value", [True, "2.5", float("nan"), float("inf"), -1])
def test_price_rejects_invalid_numeric_input(value):
    with pytest.raises(ValidationError):
        Pricing(usd_per_gpu_hour=value, usd_per_cpu_core_hour=None)

def test_bounds_rejects_reversed_interval():
    with pytest.raises(ValidationError):
        Bounds(low=2, point=1, high=3)
```

- [ ] 离线导出 `app.openapi()` 只 import app/register routes，不进入 lifespan、不 load_snapshot、不创建 out、不启动 MCP。测试把 loader/audit 替换为“若调用立即抛错”，导出仍成功。
- [ ] Node generator 读取 schema，通过锁定的 `json-schema-to-typescript` 编译，启用 unreachable definitions 导出全部网络类型，输出只有固定 banner，不含时间戳/绝对路径。Literal 的 ActionId 未必得到具名输出；生成器检测缺失时机械追加 `export type ActionId = EvaluationRequest['selected_action_ids'][number];`，禁止手抄 union。UI import ActionId/Evaluation/EvaluationRequest/ErrorResponse 的 typecheck 必须通过。
- [ ] `make contracts` 先 Python schema/OpenAPI 后 TS；`make check-contracts` 生成到临时目录逐文件比较且校验 fixtures，发现 drift 返回非零而不修改工作树。文件排序、换行和 JSON 缩进固定。

```bash
make contracts
make check-contracts
make test-api TEST_ARGS='track-2/tests/test_contracts.py -q'
npm --prefix track-2/dashboard run typecheck
```

**验收:** 第二次 contracts 不产生 diff；测试中将两个 DATA_DIR 指向同一空临时目录且 Docker 不可访问时离线生成仍成功，不删除真实数据；手改 TS 一个字段后 check-contracts 必须失败，恢复后通过。

## Task F1.6：手算 golden fixtures 与共同测试工厂

**Files:** 创建 `track-2/tests/factories.py`、`track-2/tests/test_contract_fixtures.py`、`track-2/dashboard/src/api/contracts.test.ts`；创建 `track-2/contracts/fixtures/{default-request,config,evaluation,evaluation-both-actions,evidence-cpu,evidence-idle,evidence-cpu-default,evidence-idle-standalone,job,finding,investigation,error-data-not-ready}.json`（共12份）。

**Interfaces:** `golden_snapshot() -> DataSnapshot` 返回三 job 的纯虚构 snapshot；`default_request() -> EvaluationRequest` 返回新实例。共享 helper 不 import service，不把待测函数当期望计算器。

- [ ] 固定 job 101=10 GPU-h、102=20 GPU-h、103=16 GPU-h；101 仅 CPU，102 CPU+idle（idle ceiling12），103 仅 idle（idle ceiling8）。全部 attempts=1；逐卡时长/数量/利用率、job_type、findings 与 predicate 一致，具体手算行按分析计划落实。
- [ ] 101 为 COMPLETED/batch，一张10h卡、mean/peak=0/0；102 为 COMPLETED/LLSUB:INTERACTIVE，两张各10h、mean/peak=0/0；103 为 CANCELLED/LLSUB:INTERACTIVE，两张各8h、mean/peak=2/25。各卡时长等于 job walltime；102/103 的4h门槛分别留下12/8 GPU-h；computed=.32、completed_computed=0，不能用真实样本值覆盖这些手算值。
- [ ] default-request 精确复制规范默认值；evaluation.json 对应仅 CPU，portfolio point=15、reference point=37.5；evaluation-both-actions.json 对应两行动，CPU=0/15/30、idle marginal=0/2/4、portfolio=0/17/34、reference point=42.5。
- [ ] fixtures 填齐全模型，包含 null 风险、0/1 GPU index、字符串 IDs、UNKNOWN/caveat 行口径；evidence-cpu 与 evidence-idle 均对应两行动请求且 scope=marginal，idle 行包含 job102 的 overlap 零贡献；详情 job=102。保持所有关联 finding/resource/job 可追踪。
- [ ] `evidence-cpu-default.json` 固定默认仅CPU请求、action_id=cpu_migration、scope=marginal、贡献point合计15；`evidence-idle-standalone.json` 固定相同默认请求、action_id=idle_session_reclaim、scope=standalone、贡献point合计5。两者 meta.evaluation_id 对应 evaluation.json；双行动两 evidence 对应 evaluation-both-actions.json。mock 必须按 request/action/scope 精确选文件，禁止改标签、替换 meta 或重算数字掩盖不匹配。
- [ ] 外层 meta.data_origin=`test_fixture`；Investigation 内的 origin 描述虚构场景，limitations 必含 `Hand-authored test fixture; not an investigation of the official dataset.`。不得伪造实际执行的 MCP 时间/日志或 official dataset_id。
- [ ] 生成 fixture evaluation_id 使用契约精确对象 `{dataset_id, analysis_version, request}` 的规范 JSON hash；float 字段统一 float、负零归0.0、行动按固定顺序，json.dumps 使用 sort_keys、紧凑 separators、ensure_ascii=False、allow_nan=False。对2/2.0及行动逆序设同 hash 测试；详情 evaluation_id=null。
- [ ] mock schema/status 和请求严格一致；共享 config/default fixture 不从真实数据剪切；英文 basis 写明情景与未知现金收益。
- [ ] 验证12个 JSON 同时通过对应 Pydantic 与 JSON Schema；显式断言 default15、combined17、standalone point 总和20、总 measured46；前端测试直接 import `../../../contracts/fixtures/evaluation.json` 与 both-actions 文件断言15/17，并检查四个 evidence 的 scope/hash/贡献一致，引用生成的 Evaluation 类型通过 tsc，不能复制一套改名 JSON。

```bash
make check-contracts
make test-api TEST_ARGS='track-2/tests/test_contract_fixtures.py -q'
make test-ui UI_ARGS='--run'
```

**验收:** fixtures 是独立期望值，A2 后续计算结果与之逐项比较；shared factory 不产生真实输出。fixture 页面只能显式 `VITE_USE_FIXTURES=true` 开启并显示 `Test fixture data`。

## Task F1.7：接线骨架、失败语义与并行开放门禁

**Files:** 创建 `track-2/decision/{app,routes,cli,bootstrap,service,baseline,candidates,portfolio,risk,claims,investigation}.py` 的类型/接线边界；测试 `track-2/tests/{test_route_contracts,test_bootstrap}.py`。业务函数实现按所有权转交，不以 stub 冒充成功。

**Interfaces:** 精确采用契约 §8 函数签名；`CandidateLedger` 与 `Allocation` dataclass 先定义再交 A2。app 复用 `api.main.app`，只添加 `/v1/decision` router；所有官方 routes 留在同一进程。

- [ ] F1 的 routes.py 注册全部规范路径、请求与 response_model，处理器只返回 typed 503 `DATA_NOT_READY` 与 `Decision analysis is not initialized.`；health 返回 DecisionHealth/not_ready。这样离线 OpenAPI 在 G1 已完整；A3 接手并替换处理器，禁止 fixture 回包作为生产临时实现。
- [ ] 新路由的验证/内部错误使用 ErrorResponse；按路径前缀分流，官方错误 handler 保留。测试官方未知路由仍原格式，新 evaluate 坏请求为 INVALID_REQUEST，详细错误无堆栈/凭据。
- [ ] app lifespan 使用 bootstrap.py helper 解析路径、载入只读 snapshot，F1 审计为 not_run。M2 接入后 auto 在 lifespan 后台调度真实 async run_investigation，总预算120秒含子进程启动、单调用20秒且受总剩余时间限制、业务 tools/call最多25次；tools/list握手另记日志。off 为 not_run；API ready 不等待审计结束。
- [ ] 由协调者在 M2 接入时测试：audit 协程被事件阻塞时 health/evaluate 已可返回；completed/timeout/exception 均不破坏 API。应用关闭取消后台 task 并清理 MCP 子进程；异常只写真实 failed/partial 状态，不冒充 completed。默认启动无需模型 key 或交互输入。
- [ ] `cli.py` 提供上述精确 flags；最终 team 缺失导出拒绝，HTTP claims 只返回 JSON，显式 export-claims 的 --output 才写根 claims。tools 内 validate 将 loopback:3000 明确映射 `http://dashboard:3000`，根 Make 另在宿主 curl 原 URL，不能只验证容器内联通；非 loopback URL 原样保留。
- [ ] 整理每个文件唯一 writer：A2 接手 baseline/candidates/portfolio/risk/service/claims；A3 接手 routes.py；M2 接手 investigation；U2 接手 dashboard/src 业务实现；F1 完成的共享 data/config/contracts/errors/factories 固定由协调者维护。

```bash
make check-data
make check-contracts
make test-api TEST_ARGS='track-2/tests/test_data_reuse.py track-2/tests/test_download_data.py track-2/tests/test_config.py track-2/tests/test_data.py track-2/tests/test_contracts.py track-2/tests/test_contract_fixtures.py track-2/tests/test_route_contracts.py -q'
npm --prefix track-2/dashboard run build
git status --short
```

**F1 开放门禁:** 五文件 checksum、完整共享 loader、12 fixtures、自动生成/漂移检查、类型构建全部通过；所有权表确认后才同时启动 A2/U2/M2。F1 报告记录实际命令与退出状态，并明确真实计算、真实 MCP audit、浏览器 drill-down、claims 导出、plain Compose 全流程仍由后续集成/发布门禁验证。协调者审核当前 diff 后再安排提交。
