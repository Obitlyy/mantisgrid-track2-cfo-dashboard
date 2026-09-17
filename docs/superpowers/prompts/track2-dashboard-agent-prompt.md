你负责 Track 2 的步骤2-2：React/TypeScript 决策看板。

工作根目录：
/Users/yiyangluo/Desktop/hackathon-2026-official-t1

开始前先检查并报告：桌面上还存在额外目录 `/Users/yiyangluo/Desktop/hackathon-2026-official`。它不是本任务工作根目录，不得从该目录读取、写入、运行命令或复制实现；本任务的所有路径必须位于 `/Users/yiyangluo/Desktop/hackathon-2026-official-t1`。

前置条件：
F1/G1 契约和 fixtures 已通过。你必须使用生成的 TypeScript 类型，不得自己重新定义 API 类型。

必须完整阅读：

1. /Users/yiyangluo/Desktop/hackathon-2026-official-t1/docs/superpowers/plans/2026-09-17-track2-development-plan.md
2. /Users/yiyangluo/Desktop/hackathon-2026-official-t1/docs/superpowers/specs/2026-09-17-track2-development-spec.md
3. /Users/yiyangluo/Desktop/hackathon-2026-official-t1/docs/superpowers/specs/2026-09-17-track2-contracts.md
4. /Users/yiyangluo/Desktop/hackathon-2026-official-t1/docs/superpowers/plans/track2/01-foundation.md
5. /Users/yiyangluo/Desktop/hackathon-2026-official-t1/docs/superpowers/plans/track2/03-dashboard.md

读取：

- /Users/yiyangluo/Desktop/hackathon-2026-official-t1/track-2/dashboard/
- /Users/yiyangluo/Desktop/hackathon-2026-official-t1/track-2/dashboard/src/api/contracts.generated.ts
- /Users/yiyangluo/Desktop/hackathon-2026-official-t1/track-2/contracts/fixtures/

你的任务：

1. 实现英文单页决策看板。
2. 实现三张卡：
   - Where the money goes
   - Where to cut
   - If this decision is wrong
3. 接入 config/evaluate/evidence/job/finding/investigation/claims API。
4. 支持 CPU 默认场景。
5. 支持 Idle 和双行动组合。
6. 支持 standalone/marginal 分离。
7. 支持 loading/error/empty/unknown/not_ready/partial 状态。
8. 实现证据抽屉、finding 详情、job 详情和逐卡 GPU 详情。
9. 实现 claims 下载，但不得在前端重新计算金额。
10. 实现键盘访问、dialog focus、Escape 返回、窄屏布局。
11. 编写 Vitest、Testing Library 和 Playwright 测试。

必须遵守：

- 网络字段保持 snake_case。
- 使用 contracts.generated.ts。
- 不得在前端复制 Python 财务公式。
- 不得使用 `value || 0` 消除 unknown。
- 不得把 API 失败自动切换到 fixture。
- fixture 模式必须显式 `VITE_USE_FIXTURES=true`，并显示测试数据提示。
- 生产模式默认 `VITE_USE_FIXTURES=false`。
- 不修改 Python 分析模块、Compose、Makefile 或共享契约。
- 如果发现契约问题，先报告给协调者，不要自行加字段。

完成后运行：

- make check-contracts
- make test-ui
- npm --prefix track-2/dashboard run build

报告：

1. 修改文件清单
2. 页面功能清单
3. 测试命令和真实退出码
4. 仍依赖 API/Compose 的集成项
5. fixture 模式和真实模式的区别

不要声称未执行的浏览器测试已经通过。

---

新增部分：A1 双视图决策看板与 3D 机房问题地图

必须额外完整阅读以下视觉参考代码：

1. 最终布局、交互和机柜组合参考：`/Users/yiyangluo/Desktop/hackathon-2026-official-t1/docs/superpowers/references/track2-dashboard/a1-final-layout-detailed-racks.html`
2. 机柜建模清晰度参考：`/Users/yiyangluo/Desktop/hackathon-2026-official-t1/docs/superpowers/references/track2-dashboard/a1-modeling-clarity-target.html`
3. 视觉参考使用说明：`/Users/yiyangluo/Desktop/hackathon-2026-official-t1/docs/superpowers/references/track2-dashboard/README.md`

产品方向：

- 实现 `Monochrome Executive Dashboard with Switchable Facility Tour`。
- 同一个英文单页应用提供两个可切换视图：`Executive View` 与 `Facility Tour`。
- 两个视图必须使用同一份 evaluation、筛选条件、当前步骤、已选 action/finding/job/GPU 和证据上下文。切换视图不得重新计算、丢失选择或改用另一套数据。
- `Executive View` 负责让 CFO 快速理解数字并做决定；`Facility Tour` 负责用空间方式定位问题和展示证据。3D 场景不得成为与决策数据脱节的装饰。

新增任务：

12. 在页面主要导航区域实现清晰的双模式切换：
    - `Executive View`
    - `Facility Tour`
    默认进入 `Executive View`。切换控件必须可通过键盘操作、具有明确 active 状态，并保留当前决策上下文。
13. 在 `Executive View` 首屏实现四项 CFO 摘要。字段名称可依据生成契约调整，但语义必须覆盖：
    - observed GPU spend
    - recoverable cost range
    - gap to the 20% target
    - downside if the decision is wrong
    所有数字必须来自 API；展示为美元、GPU 小时或容量百分比。缺失、unknown、not_ready 或 partial 时显示明确状态，不得补零或伪造精确值。
14. 将三张决策卡升级为可视化决策区域，不得只用大段文字和 metric 列表表达：
    - `Where the money goes`：至少提供成本流向/瀑布表达和 outcome 比例表达，清楚区分 completed、cancelled、failed、timeout 与 unknown；不得把 cancelled 直接等同浪费。
    - `Where to cut`：至少提供行动排名图，以及 savings 与 downside 的比较视图；支持 CPU 默认场景、Idle、双行动组合，并明确区分 standalone 与 marginal。
    - `If this decision is wrong`：至少提供 low/point/high 范围表达，并显示受影响的容量、工作负载或其他 API 已提供的风险维度。
15. 图表必须服务于 CFO 决策：直接标注关键值和单位，提供简短结论，避免依赖 hover 才能看见核心数字。金额、区间和风险不得在前端重新计算；只允许对 API 已返回的数据进行格式化和可视编码。
16. 所有图表必须有可访问的数据摘要或等价表格。不得只依赖颜色区分系列、状态和风险；使用标签、图标、轮廓、线型、纹理和明暗共同编码。
17. 图表、三张决策卡、3D 机柜和证据抽屉必须联动：
    - 在 `Executive View` 选择 action、finding、job、GPU 或图表数据点后，切换至 `Facility Tour` 应聚焦对应机柜或模块。
    - 在 `Facility Tour` 选择机柜或模块后，返回 `Executive View` 应保留选择，并定位或高亮对应决策内容。
    - 两个方向都必须保持 dataset_id、evaluation_id、action_id 和 scope 一致。
18. `Facility Tour` 使用虚拟机柜布局展示 225 台机器。界面必须持续显示 `Decision layout — not physical rack location`，不得暗示这些位置是真实机柜坐标。
19. `Facility Tour` 提供两种交互模式：
    - `Guided Tour`：使用手动三步导航，不得自动播放。
    - `Free Explore`：允许用户旋转、缩放、选择机柜和模块，并能一键返回全局视角。
20. `Guided Tour` 的三个步骤为：
    - `01 / SPEND` 对应 `Where the money goes`
    - `02 / ACTION` 对应 `Where to cut`
    - `03 / DOWNSIDE` 对应 `If this decision is wrong`
    用户点击步骤后才允许镜头移动；切换动画目标约 700ms，必须可中断。点击机柜不得自动改变当前步骤。
21. 点击异常机柜或 GPU 模块时：
    - 镜头平滑靠近选中对象。
    - 其他机柜降低视觉权重，但仍保留空间上下文。
    - 选中模块提高轮廓和材质对比度。
    - 在设备附近显示附着式悬浮信息标注。
    - 标注展示 API 已返回的行动、金额或 GPU 小时区间、容量比例、责任角色、风险状态和 `View evidence` 入口。
    - 不得在标注中自行计算金额、区间或风险。
22. `View evidence` 必须复用既有 EvidenceDrawer、finding、job 和逐卡 GPU 详情流程。关闭 dialog、按 Escape 或返回后，焦点必须回到触发元素。

视觉系统：

23. 全部界面使用银、黑、白、灰的单色视觉系统：
    - 页面与机房背景：白色、暖白或浅灰。
    - 机柜主体：碳黑、石墨灰。
    - GPU 模块：拉丝银、冷灰。
    - 文字：黑色、深灰。
    - 边框、网格与辅助线：银灰、浅灰。
    - 选中状态：高亮银白轮廓或更强的明暗对比。
    禁止使用蓝色科技风、彩虹图表、霓虹网格、发光雾效和常见“AI 控制室”视觉。
24. 业务状态同样使用灰阶表达，不使用绿色、黄色、橙色或红色作为常规状态色。通过实线/虚线/双线轮廓、斜纹、点阵、图标、标签和明暗层级区分 healthy、investigate、confirmed issue、unknown、not_ready、partial 与 cannot_determine。unknown、not_ready、partial 和 cannot_determine 不得使用与 confirmed issue 相同的视觉编码。
25. 图表采用可辨识的灰阶设计。相邻系列必须具有足够明度差异，并辅以标签、纹理或线型。不要制作多个无法区分的浅灰色系列；不要使用仪表盘装饰或无意义动画代替可比较的刻度。
26. 机柜建模必须清晰到模块级：需要可辨识的机柜框架、U 位、导轨、拉丝银模块、通风孔、把手、设备标签和状态灯。状态灯也使用白灰明暗或形状编码，不得使用彩色发光覆盖模型细节。
27. 保留参考中的空间布局：白灰机房背景、中央通道、两侧机柜、右侧或设备附近的悬浮信息，以及底部三步手动导航。默认 Facility Tour 必须先显示机房整体，不得改成单机柜特写。
28. 表现优化包括：清晰机柜边缘、金属材质、柔和环境光、接触阴影、克制且可中断的镜头运动、选中对象的银白轮廓，以及数据变化时的短暂过渡。表现效果不得降低文字、图表或证据的可读性。

实现、性能与降级：

29. 3D 实现优先采用 React Three Fiber/Three.js 的程序化或本地 GLB 资产。所有运行时资产必须本地提供，不得依赖 CDN。若所需依赖不在现有 lockfile，先向协调者报告，不得自行修改共享 package/lock、Compose 或 Makefile。
30. 相同机柜和模块使用 instancing；提供近景/远景 LOD、抗锯齿和可降级阴影。远景可以简化模型，靠近后展示模块细节。
31. 低性能、WebGL 不可用或 3D 初始化失败时，显示等价的可访问二维机房矩阵。二维模式必须支持选择机器、查看状态、打开证据和返回三张决策卡，不得阻断 CFO 的主要决策流程。
32. 遵守 `prefers-reduced-motion`：减少动态时禁用飞行动画并立即切换镜头。提供清晰的全局返回操作。窄屏下可以使用机柜列表或二维矩阵配合局部 3D 预览，但必须保留核心数字和证据路径。
33. 为新增可视化与交互补充测试，至少覆盖：
    - 默认进入 `Executive View`。
    - 双视图切换保留当前 evaluation 和选择。
    - 四项 CFO 摘要正确显示 API 值及 unknown/partial 状态。
    - 三个决策区域存在可访问图表摘要或等价表格。
    - standalone 与 marginal 不会混合。
    - 手动步骤不会自动前进。
    - 镜头只在用户操作后切换。
    - 机柜状态包含文本标签，并且不依赖颜色表达。
    - unknown、not_ready、partial 和 cannot_determine 不会渲染为 confirmed issue。
    - `View evidence` 使用当前已应用 evaluation。
    - reduced-motion、二维 fallback、键盘操作和窄屏布局可用。

视觉参考文件是布局和材质示例，不是可直接交付的业务实现。示例金额是假数据，禁止复制到生产 UI、测试预期或 claims。最终所有金额、状态、节点、行动和图表数据必须来自生成契约与 API 响应。
