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

新增部分：A1 3D 机房问题地图

必须额外完整阅读以下视觉参考代码：

1. 最终布局、交互和机柜组合参考：`/Users/yiyangluo/Desktop/hackathon-2026-official-t1/docs/superpowers/references/track2-dashboard/a1-final-layout-detailed-racks.html`
2. 机柜建模清晰度参考：`/Users/yiyangluo/Desktop/hackathon-2026-official-t1/docs/superpowers/references/track2-dashboard/a1-modeling-clarity-target.html`
3. 视觉参考使用说明：`/Users/yiyangluo/Desktop/hackathon-2026-official-t1/docs/superpowers/references/track2-dashboard/README.md`

新增任务：

12. 在英文单页决策看板顶部实现 A1 3D 机房问题地图，作为三张决策卡的空间化入口；不得删除或弱化三张卡及其证据链。
13. 3D 场景使用虚拟机柜布局展示 225 台机器。界面必须持续显示 `Decision layout — not physical rack location`，不得暗示这些位置是真实机柜坐标。
14. 使用手动三步导航，不得自动播放：
    - `01 / SPEND` 对应 `Where the money goes`
    - `02 / ACTION` 对应 `Where to cut`
    - `03 / DOWNSIDE` 对应 `If this decision is wrong`
15. 用户点击步骤后才允许镜头移动；切换动画约 700ms，可中断。点击机柜不得自动改变当前步骤。
16. 点击异常机柜或模块时显示附着在设备附近的悬浮信息标注。标注展示 API 已返回的行动、区间、责任角色、风险和 `View evidence` 入口；不得在标注中自行计算金额。
17. `View evidence` 必须复用既有 EvidenceDrawer、finding、job 和逐卡 GPU 详情流程，保持 dataset_id、evaluation_id、action_id 和 scope 一致。
18. 视觉基准使用现实工业机房：白色/浅灰背景、碳黑机柜、拉丝银 GPU 模块。避免大面积蓝色、霓虹网格、发光雾效和常见“AI 控制室”配色。
19. 状态色只占小面积：绿色表示健康，琥珀色表示需要优化或证据不足，红色只用于有充分故障证据的高风险节点。unknown、not_ready、partial 和 cannot_determine 不得渲染为确定故障。
20. 机柜建模必须清晰到模块级：需要可辨识的机柜框架、U 位、导轨、拉丝银模块、通风孔、把手、设备标签和状态灯；状态光不得遮盖模型细节。
21. 保留参考中的整体布局和交互：白灰机房背景、中央通道、两侧机柜、右侧悬浮信息及底部三步手动导航。机柜细节可以提高，但不得改成单机柜特写作为默认首页。
22. 3D 实现优先采用 React Three Fiber/Three.js 的程序化或本地 GLB 资产。所有运行时资产必须本地提供，不得依赖 CDN。若依赖不在现有 lockfile，先向协调者报告，不得自行修改共享 package/lock、Compose 或 Makefile。
23. 相同机柜和模块使用 instancing；提供近景/远景 LOD、抗锯齿和可降级阴影。低性能或 WebGL 不可用时显示等价的可访问二维机房矩阵和三张决策卡，不得阻断决策流程。
24. 遵守 `prefers-reduced-motion`：减少动态时禁用飞行动画并立即切换镜头。键盘用户可以选择三个步骤、聚焦机柜、打开证据和返回触发元素。
25. 为新增交互补充测试：手动步骤不会自动前进；镜头只在用户操作后切换；机柜状态包含文本标签；unknown/partial 不会变成红色故障；`View evidence` 使用当前已应用 evaluation；reduced-motion 和二维 fallback 可操作。

视觉参考文件是布局和材质示例，不是可直接交付的业务实现。示例金额是假数据，禁止复制到生产 UI、测试预期或 claims。最终所有金额、状态、节点和行动必须来自生成契约与 API 响应。
