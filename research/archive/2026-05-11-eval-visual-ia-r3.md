# Round-3 视觉 + IA 合并评审 · impl-explain demo

评估基于 r3 `fullpage.png`（1400×5800），与 r2（1200×5500）按 named region 逐段对照，并核对 `scripts/render.py` 实际 CSS。

---

## A. Round-2 P0/P1 验证（逐条）

1. **Before/After 空白** —— 主要病灶解决，但走到另一极端：`align-items: start` 之后 AFTER cell 高度只有 ~110px、BEFORE cell ~310px，两 cell 错落明显（详见 B1）。
2. **Risk Snapshot 移位** —— 现在跟在 Risks 标题之下、与第一条 risk-row 紧贴，结构合理。但 Top risk highlight 与下面 risk-row 的第一条 100% 同文重复，inline 不是好补充而是冗余（详见 B 段重点）。
3. **47 → 1 单 chip** —— 44px Fraunces 600 + 红 mono hint，重量合适，单独一项不显孤单；左边一长串 plan path / commits 占据视觉余量，hero 整体平衡。
4. **删 decision question** —— 卡片节奏明显紧凑，01–05 视觉缩短约 1 行，整段连贯不残缺。删得对。
5. **删 Risks meta line** —— 由于 Snapshot 紧接 section title，meta line 缺失感被填补，没有突兀。OK。
6. **Summary upright** —— 截图中 "叙述" mono eyebrow + Inter 16px 正体与 hero subtitle 26px italic 完全区分，撞角色问题解决。但出现新问题（见 B4）。
7. **Hero value 44px / 600** —— 与 h1 64px Fraunces 同字族不冲突，权重 600 比 h1 的 500 更重但因为字号小没有压过，OK。

P0/P1 七条里 5 条干净落地，1 条（B/A 空白）矫枉过正，1 条（Top risk inline）变成新问题。

---

## B. Round-3 新引入的问题（重点）

### B1. Before/After 高度严重失衡 — **P1**

CSS 改成 `align-items: start` 让 cells fit-content，AFTER 是横向 5 节点单链（占满宽度但只用 ~80px 高度），BEFORE 是垂直多分支（~280px 高度），两 cell 高度差 ~3.5×。视觉上 AFTER 像"没画完"，与"收敛"叙事相反。r2 的"对比叙事"目标其实没达成。
**建议**：BEFORE/AFTER 都改用 `flowchart TB`（top-bottom）让两侧都纵向，或回到 stretch + AFTER `.mermaid` 内部 `align-items: center`（r2 评估的第一方案）+ 给 AFTER cell 加一行 caption（如 "5 → 1 dispatcher"）填底部。

### B2. Risk Snapshot 移位的"丢失风险"——次方案缓解了但不彻底 — **P1**

Snapshot 已搬到 Risks 顶部，但 IA r2 明确建议同时在 TL;DR 尾加 `5 risks · 1 high (已缓解)` 单行兜底——**r3 没加**。Architecture / Decisions 这两屏完全没有任何风险信号，30 秒读者如果只滑到 Decisions 就走人，会拿不到"高危是哪条 / 缓没缓"的信息。
**建议**：TL;DR section 末加一行极简提示，比 Top risk inline 卡更重要。

### B3. Top risk highlight 与第一条 risk-row 100% 重复 — **P1**

`render_risk_snapshot` 选最高 severity，本例就是唯一的 high。highlight 卡的 description 与 `risk-list` 第一行 desc 是同一段 `r["description"]`，note 不同但描述部分一字不差。视觉上读者刚读完 Top risk 卡，紧接着又看到同一句作为 HIGH 行的 description，会感觉"为什么又来一遍"。
**建议**：高亮卡用 `note`（"切换文档要求重启服务：lifespan 内 ... 不会同时挂载两套"）替代 description；或者高亮卡保留时把 risk-list 里这条折叠为只显示 note。

### B4. Top risk 的色彩信号与数据耦合——demo 永远是绿色 — **P0（设计层面）**

CSS 里 `.risk-highlight` 默认是红（rgba(122,47,36,0.06) + sev-high 左边框），`.mit` 变体是绿（rgba(74,106,44,0.06) + mit-full 边框）。demo 输入唯一的 high 风险 `mitigation: "full"`，所以渲染出的永远是绿卡 + "TOP RISK (已缓解)"。读者看到的是"放心信号"，红警从不出现。这意味着 r3 视觉上"风险高亮系统"的告警态在示例文档里完全不可见——可能给落地的其他 case 留下设计黑洞（如果只用这份 demo 自测，UI 不会暴露 red 态的字号、border、与暖色 cream 背景的对比是否够）。
**建议**：选 demo 时混入一条 `severity: high, mitigation: none` 的风险；或测一份双 demo（mitigated / unmitigated）确认两种态视觉强度都对。

### B5. TOC active link 在页顶就高亮 BEFORE/AFTER — **P2**

hero 截图里 sticky TOC 显示 "BEFORE / AFTER" 是红色 active 态，但实际滚动位置在页顶。说明 scroll-spy / IntersectionObserver 的初始状态有 bug 或者默认 highlight 第三项。读者扫一眼会以为"已经看过的"或"当前在的"——歧义。
**建议**：active 由 `scroll-spy` 计算，页面初始位置应高亮 TL;DR 或不高亮任何项。

### B6. 暖色融入度——OK，但 Top risk 绿框略冷 — **P2**

`rgba(74,106,44,0.06)` 在 cream 上几乎透明，左边框 3px 实色 olive 与全站 chosen-line 同色，融入度好。红卡（实际渲染不出现，仅静态 CSS）`rgba(122,47,36,0.06)` 与 hint accent 同色系，也兼容。颜色块本身不破和；问题只在 #B4 的"看不见红"。

---

## C. R1/R2 都没识别的问题

1. **Commits 5 行仍在 hero**——IA r2 P0 建议挪到 footer / 折叠区，r3 没动。hero 高度 ~880px，commits 占 ~120px，单页阅读时仍是"audit trail 堆在门面"。如果接下来要砍，这是最大的 hero 节省点。
2. **"待观察 / 部分缓解" mit 列的字号与 sev 列不平衡**——risk-row 右栏 mit 是 10px mono，左栏 sev 也是 10px mono，但中间 desc 是 16px Inter——三栏字号对比下右栏 mit 显得"过细几乎读不出来"。可以把 mit 涨到 11px 或加 `font-weight: 600`，让"是否缓解"这一关键状态读得到。
3. **Decisions section 顶部 `6 decisions · 5 chosen · 1 deferred` meta**——r2 视觉评估 §7 已指它信息冗余但优先级 P2，r3 没动。现在和"删除 risks-meta"的处理对称感被破坏：risks 这边删了、decisions 这边留，结构不对称。要么两边都留要么两边都删。
4. **Top risk highlight 没有锚点跳转到对应 risk-row**——读者读完高亮想知道"细节在哪一条"，没有 `<a href="#risk-r1">→</a>`。risk-list 也没给每条加 id，跨段引用难做。

---

## D. Round-4 判断

**B1 / B2 / B3 / B4 都是 P1 或 P0，不是 P2 微调**——尤其 B3 的"高亮与首条 risk-row 重复"是 round-3 引入的新冗余，B4 的"demo 看不见红警"是设计盲区，B2 是 IA r2 已明确写出但 r3 漏做的兜底。这三处加起来仍能显著提升首屏对齐密度。

C 段的 4 条里有 1 条（commits 挪走）是 IA r2 P0 遗留，剩下 3 条是 P2。

**建议进入 round-4**，但只做窄范围：(a) Before/After 高度策略二选一并补 AFTER caption；(b) 把 Top risk 改成 note 内容、避免与首行重复；(c) TL;DR 尾加 `5 risks · 1 high (已缓解)` 兜底行；(d) 换/补一条未缓解 high 风险的 demo 输入，确认红警视觉可用。其余（B5/B6/C 全部）可以一起带或留 r5。
