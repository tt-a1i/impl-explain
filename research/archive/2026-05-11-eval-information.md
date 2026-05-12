# impl-explain Demo 报告 · Reader IA / UX 评估

> 视角：团队成员，没参与这次实施，开会前 30–60 秒扫一眼想对齐"做了啥 / 为啥 / 要小心啥"。
> 评估对象：`unified-source-sync-manager` 渲染产物（6 屏，约 5500px 高）。

---

## 1. Section 顺序：当前合理，但"权衡的代价"埋得太深 (P1)

当前顺序 Hero → TL;DR → Architecture → Decisions → Before/After → Risks → Out of Scope，是"先抽象后具体"的写作惯例，没问题。但对 30 秒读者来说有两处不合理：

- **Before/After 应当紧跟 Architecture 之前或之后**，而不是夹在 Decisions 和 Risks 中间。当前位置导致读者读完 6 张决策卡才看到"到底变了什么"，此时已经 3–4 屏滚动距离。**建议**：把 Before/After 提到 Architecture 正下方（同属"结构变化"），形成 "TL;DR → 静态结构 (Architecture) → 动态变化 (Before/After) → 为什么这么变 (Decisions) → 风险 → 边界"的认知曲线。
- **Risks 太靠后**。Risks 是开会场景里最高频被问的内容（"这玩意儿上线会炸吗？"），现在埋在第 6 屏。**建议**：在 TL;DR 下方加一行 "Risk Snapshot"（例如 `5 risks · 2 mitigated · 1 high`），让读者在第一屏就拿到风险姿态，详细列表保留在底部。

## 2. 30 秒能拿到对齐信息吗：勉强，TL;DR 的"方案"段太长 (P0)

Hero + TL;DR 三句覆盖 "做了啥 / 怎么做 / 代价"，结构正确，但 "方案" 一段塞了 4 个组件名 + 一个 env flag + 一个抑制策略，扫读时眼睛会卡在 `SourceSyncDefinition / SourceSyncService / SourceSyncScheduler / SOURCE_SYNC_ENABLED` 这堆驼峰里。

**建议**：
- "方案"句子拆成 **两个并列短句**：`新增 注册表 + 调度器 + 派发服务` 一句；`SOURCE_SYNC_ENABLED 灰度切换` 一句。
- 在 Hero 副标题或 TL;DR 顶部加一组 **hero metric**（建议 3 个）：`6 decisions · 5 risks (1 high) · 4 sources unified`。reader 一眼掂量这次改动量级，比 "git range" 直观得多。
- `plan` 和 `range` 两行**降权**：现在视觉重量和副标题接近，但 reader 在 HTML 里不会去点 plan 文件。改成更浅的 muted style 或塞进角落的 metadata block。

## 3. 信息密度逐 section

- **Hero（P1）**：副标题信息够，但缺"量级感"。加 hero metric（见上一节）。
- **TL;DR（P1）**：三句话覆盖够，但建议把字段名从 "目标 / 方案 / 权衡" 改成 **"做什么 / 怎么做 / 代价是什么"**——更口语，更适合 30 秒读者。`权衡` 是中性词，`代价` 把 tradeoff 的方向说清了。
- **Architecture（P2）**：mermaid 图没问题，但**缺一行 caption** 解释"新组件高亮（橙色 = 这次新增）"。读者不知道颜色编码就 decode 不出"新 vs 旧"。**建议**：图下方一行 italic caption：`橙色块 = 本次新增；箭头标签 = dispatch kind`。
- **Decisions（P0，见 §4）**：6 张连续卡片在没有 TOC 的情况下是滚动负担。
- **Before/After（P2）**：两张图并列对比很好，但**箭头 "spawn ×47" 是这次改动最戏剧化的数字**，应该在 TL;DR 里也提一次（呼应"4 sources unified"的 hero metric）。
- **Risks（P1）**：severity 染色 + mitigation 状态够，但**缺一行汇总**：`Total 5 · High 1 (mitigated) · Medium 2 · Low 2 (1 mitigated)`。读者扫完想立刻知道"未缓解 high risk 有几个"。
- **Out of Scope（OK）**：italic 列表合适，不该再加权重。

## 4. 决策卡片字段结构：命名和顺序都要调 (P0)

当前字段：`question → chosen → rationale → rejected → cost → status`。

问题：
- **`question` 用问号结尾的中文长句**（"数据源 cadence/dispatch 信息放哪？"）作为卡片标题，扫读时是认知负担。reader 想要的不是"题目"，而是"这条决策定了什么"。**建议**：标题改成**结论式短句**（如"注册表集中放 cadence"），把原 question 作为副标题。
- **`rejected` 排在 `rationale` 后面**，但 rationale 已经在解释"为什么选 chosen"，rejected 此时再出现，节奏倒退。**建议**字段顺序改为：`chosen (结论) → rationale (为什么) → rejected (考虑过的替代) → cost (代价) → status`。
- **字段命名"采用 / 反对 / 代价"**：`反对` 不准确（不是反对，是"考虑过但放弃"）。**建议**改成 `采用 / 放弃 / 理由 / 代价`，或英文 `Chosen / Rejected / Why / Cost`。
- **`status: deferred` 视觉上没有区分**（截图里第 6 张卡片 status 是 deferred，但视觉权重和 chosen 一样）。**建议**：deferred 卡片整体降饱和度或加 `[DEFERRED]` 角标，让读者一眼分辨"这个还没定"。

## 5. 可发现性：5500px 高必须有导航 (P0)

当前没有任何导航，reader 滚到第 4 屏后丢失方位感。

**建议**（按优先级）：
1. **顶部 sticky TOC**：7 个 section 横排小字，当前位置高亮。占用一行高度即可。
2. **Decisions 卡片左侧编号 `01–06` 已经做了**，但建议在 TOC 里把决策标题也列出来（折叠/展开），方便从开会场景里直接跳到"那条关于 retry 的决策"。
3. **顶部 progress bar**（1px 高的填充条）：成本极低，对长报告导航感增益明显。
4. **不需要折叠 Decisions**：6 张是上限，折叠后反而增加点击成本；超过 8 张时再考虑。

## 6. 缺什么 / 多什么

**缺**（按优先级）：
- **P0 · Risk Snapshot 一行**（在 TL;DR 和 Architecture 之间）：`5 risks · 1 high (mitigated) · 2 unmitigated medium`。
- **P1 · "What changed at a glance" 一行 metric**（Hero 下）：sources unified、loops removed (47→1)、env flag。
- **P2 · Architecture caption**：解释颜色和箭头含义。
- **P2 · Decisions 顶部一行汇总**：`6 decisions · 5 chosen · 1 deferred`。

**多 / 可删**：
- **`plan` 和 `range` 两行 metadata** 在 Hero 区视觉权重过高。降权或挪到页脚。reader 在 HTML 里基本不会跳出去看 plan 文件。
- **Out of Scope 6 条偏多**，其中 `Per-source 自定义 timeout` 和 `失败重试策略` 已经在 Decisions 里隐含说过。可以裁到 3–4 条核心边界。

## 7. TL;DR 的"权衡" vs Decisions 的"代价"：是冗余 (P1)

TL;DR 的 `tradeoff: 多一层注册表抽象，换来"新增一个数据源去哪里加"从 grep 八处变成一处` 和 Decision 01 的 `cost: 多一层抽象；新增 source kind 时需要在 SourceSyncService._run_definition 加分支` 高度重叠。

**怎么区分**：
- **TL;DR 的"权衡"应该是整体方案的 net tradeoff**——一句话答 "this change 带来的总账"。建议改写成更宏观："换走 47 个 per-feed loop 的复杂度，引入 1 个调度器单点故障风险"。
- **Decision.cost 是单点决策的本地代价**——只描述这一条决策选了 A 而不是 B 的代价，不重复整体故事。Decision 01 当前的 cost 写法就是局部的，没问题；问题在 TL;DR 的 tradeoff 写得也太局部，向 Decision 01 看齐了。

或者更简单的规则：**TL;DR.tradeoff 只能引用 Decisions 里没说过的角度**（架构总账、运维总账），而不是复述某一条决策。

---

## 如果只能改 3 处信息架构

1. **【P0】把 Risk Snapshot（一行汇总 + severity 计数）放到 TL;DR 正下方。** 开会场景最高频问题是风险，目前埋在第 6 屏。
2. **【P0】决策卡片标题改成结论式短句**（不是问号），字段顺序调整为 `chosen → rationale → rejected → cost`，deferred 状态视觉降饱和度。读者扫卡片时眼睛跟的是"定了什么"，不是"在问什么"。
3. **【P0】加顶部 sticky TOC + progress bar。** 5500px 没有导航，从开会引用场景（"看第 4 条决策"）到回滚阅读都是负担。

次优：Before/After 上移紧贴 Architecture；Hero 增加 hero metric 三连；TL;DR 字段改 "做什么 / 怎么做 / 代价"。
