# Round 2 视觉评审 · impl-explain demo

评审范围：仅视觉层。基于 `fullpage.png` (1200×5500) 与 `wide-fullpage.png` (1400×5800)，
对照 `scripts/render.py` 当前 CSS / mermaid theme。Round-1 已修项不再赘述。

---

## 1. TOC + Progress Bar 的视觉融入度

**P2 · 基本 OK，但有两处可调。**

- 半透明 `rgba(250,247,242,0.92)` + `backdrop-filter: blur(10px)` 在 cream 上几乎隐形，
  不显突兀；进入视区时只看见 `border-bottom: 1px var(--rule)` 的发丝线，节制。
- 实际问题在 **滚动遮挡**：TOC 高度大致 44–48px，但 `section { scroll-margin-top: 80px }`
  只给了 80px。锚点跳转时 section-title 距 TOC 底缘仅 ~32px，视觉太挤。建议
  `scroll-margin-top: 96px`。
- TOC active 态用 `color: var(--accent)` + `border-bottom: 1px solid var(--accent)`。
  下划线和 TOC 自己底部那条 `--rule` 平行，会看成"两条线对齐"。把 active 下划线改
  `border-bottom-color: currentColor; border-bottom-width: 2px`，并把 padding-top
  从 2px 收到 0，让 active 标签与 TOC 底缘的 rule 在视觉上"咬合"而不是"叠"。
- 进度条 `height: 2px` 在 cream 上 accent 红明显。可考虑 `height: 3px` 让它更像"实体"
  而不是"细线"——cream 背景吞细线。

## 2. Hero Metric Chips 的视觉重量

**P1 · 数字太轻、与 subtitle 撞间距。**

- 38px Fraunces 数字 + 10px mono label，整体看上去**比 26px italic subtitle 还轻**
  （Fraunces 500 在 38px 时 stem 偏细，italic subtitle 又有色彩饱和度优势）。
  hero 节奏：标题 64 → subtitle 26 italic → metrics 38 → meta 11，metrics 这一档
  其实应该是仅次于标题的次重元素，现在被夹在两个偏冷的灰色 label / mono 块之间，
  存在感不够。
- 改值建议：
  - `.hero-metric .value`: `font-weight: 500` → `600`；`font-size: 38px` → `42px`；
    `letter-spacing: -0.015em`（再紧一点）。
  - `.hero-metric`：上下加 12px 左右的 baseline 锚点感，可以给容器
    `padding-bottom: 4px; border-bottom: 1px solid transparent`，hover 时
    `border-bottom-color: var(--rule)`——让 chip 像"可点查询条目"。
  - 间距：当前 `gap: 16px 48px`，与下方 `.report-meta` 的 `padding-top: 32px`
    之间空气过大。`.hero-metrics { margin: 0 0 32px }`（当前 36px）+ 把 `.report-meta`
    顶部分隔线挪到 hero-metrics 之上（让 metrics 在分隔线下方与 plan/commits 同栏），
    或者保持现在结构但把 margin 收到 28px。
- "1 HIGH" hint 是橙色，在 5 风险旁边 —— 整 hero 唯一非 cream/text 的色块，挺好。
  保持。

## 3. Risk Snapshot 段

**P1 · 卡片高度 / 内容布局基本 OK，但与下方 Architecture 之间过空。**

- 卡片本身 24×28 padding + flex wrap，节奏舒服。pill 用 12px 圆角
  + 10px mono + 透明度 0.12 背景，是整页**唯一的圆角元素**——和其他全部
  `border-radius: 0/2px` 撞了。两条改法：
  - **A（保留圆角，强化"chip 系"）**：把 hero-metric value 也做成 chip 风格
    （加 4–6px 圆角背景），让 chip 形成一个体系。
  - **B（统一全页非圆）**：`.risk-snapshot .pill { border-radius: 2px }`，
    跟 diagram-wrap / flow-cell / chosen-line 一致。我倾向 B。
- "5 risks" 的 `.word` 用 italic + 14px 与 `.num`（24px Fraunces）共行，
  italic 在 mono pills 旁有点"过度装饰"。把 `.word` 改 `font-style: normal`，
  保持 14px mono `font-family: 'JetBrains Mono'`，整段更克制。
- 与下方 Architecture section 之间用了 `section { margin-top: 80px }`，但 risk-snapshot
  自己已经有 `margin-top: 56px`。两段加起来 risk-snapshot 上下都很"独"。考虑把
  risk-snapshot 当作 TL;DR 的一部分（移到 TL;DR section 内、共用一个 section 容器），
  这样上下气场连续，也避免 #4 提到的 "summary 角色重叠"问题。

## 4. Architecture summary 段

**P1 · italic 撞角色 + 字号梯度模糊。**

- summary（17px italic Fraunces）和 hero subtitle（26px italic Fraunces）确实**角色重叠**
  ——读者会把它当 "subtitle 续集" 而不是 "diagram 引导"。问题不在 italic 本身，
  在于 hero subtitle 已经用掉了 italic Fraunces 这张牌。
- 更糟的是 summary（17px italic）和 diagram-caption（14px italic）**也撞**——
  一段图前 italic + 一段图后 italic，读起来像"两个旁白"。
- 建议二选一：
  - **方案 A（推荐）**：summary 改 upright Inter 17px line-height 1.65，前面加一个
    mono eyebrow（如 "概览 ·"），caption 保持 italic Fraunces 14px。这样 italic
    只用于 figure caption / cost / question 三处装饰角色，hierarchy 清晰。
  - **方案 B**：summary 保持 italic 但字号上提到 20–22px，font-weight 400，
    `color: var(--text)` 不是 `text-soft`——让它升级成"图的导读句"，
    caption 14px italic 自然次级。
- 现在两段都 italic + 灰，区分不开。

## 5. Decision title vs question 双层标题

**P2 · 层级勉强能看，但 question 太小、margin 太紧。**

- 27px title + 15px italic question，字号比 1.8:1，按经典 type scale 应该够分明。
  但 question 紧贴 title 下方 `margin: 0 0 16px`，且字色 `text-muted (#8a8275)`
  在 cream 上对比度刚到 4.5:1 边界，读起来"塌"在 title 脚下。
- 改值：
  - `.decision .title { margin: 0 0 6px }`（当前 4px，给 question 留一点呼吸）。
  - `.decision .question { margin: 0 0 20px; font-size: 16px }`（15→16 略大）。
  - 颜色保持 `text-muted` OK，因为 italic 已经有"角色降级"的语义；不要加深变 `text-soft`，
    会和 rationale 撞。
- title declarative 27px 与下方 chosen-line text 15px 的视觉拉力其实最强——
  这一层已经达成了 "answer-first" 的设计目标，保留即可。

## 6. Decision ::after 发丝分隔

**P2 · 位置和长度都太弱。**

- 32×1px 的发丝放在 `left: 88px`（与 num 列右缘对齐），实际看上去就是**很小一段**，
  距下一条 num 还有 36px。两条决策之间已有 72px 大间距，再加这个发丝其实没起到
  "明确分隔"作用，反而像"残留装饰"。
- 改：
  - **方案 A（删）**：直接去掉 `.decision::after`，靠 72px gap 自然分隔。最干净。
  - **方案 B（强化）**：长度 32 → 80px，位置改 `left: 0`（横跨 num 列），
    `bottom: -36px` → `-28px`，让它真正贡献"章节段落分割"的视觉重量。
- `:last-child::after { display: none }` 检查 fullpage 截图最后一条决策 06 下方
  没有发丝、紧接 Risks section，逻辑生效。OK。

## 7. Decisions / Risks meta line

**P2 · Decisions 那条多余；Risks 那条恰好够用。**

- `6 decisions · 5 chosen · 1 deferred` 与 hero-metric 的"决策 6"是重复信息，
  且 hero 那个数字更显眼。删掉 decisions-meta 或改成更窄的功能：列举 deferred 的
  编号链接，比如 `1 deferred (→ 06)`，方便扫到。当前形态属于"凑信息密度"。
- `5 total · 1 high · 2 medium · 2 low · 1 mitigated` 在 Risks 段里有用：
  Risks 段被 risk-snapshot 提前预览过，meta-line 这条作为表格"列汇总"是合理的
  数据补完。保留。
- 一致性：删掉 decisions-meta 后 Risks 这条略孤单，可以考虑把它也并入 risk-snapshot
  那张卡片底部（cf §3 的 section 合并思路）。但优先级 P2。

## 8. Risk Snapshot vs Risks 段重复

**P1 · 信息确实冗余，但分工可以救。**

- 当前 snapshot 给"3 类 × 数量 + 缓解占比"，下方 Risks 表给"逐条描述 + note + mit 状态"。
  从信息层面**不重复**，但视觉上两个 "Risk-themed block" 间隔不到一屏，体感冗余。
- 救法：
  - snapshot 卡里加锚点跳转：`<a href="#risks">→</a>`，承诺"下面有详情"。
  - snapshot 里 pill 文案改进，`1 HIGH (ALL MIT)` 当前有点"标签写满"。
    建议 `1 HIGH · MITIGATED`（用分隔点而不是括号），mit 状态用 opacity 而不是
    `(0 mit)` —— `0 mit` 这种 zero state 反而是噪声。
  - 如果 snapshot 与 #3 建议合并到 TL;DR section 内（变成 TL;DR 的第 4 行），
    那么 Risks 段才是"展开"——两段的关系从重复变成 summary→detail，自然。

## 9. 整体节奏 vs Round-1

**P0 · 一处严重问题（After 图空白）+ 一处节奏空。**

- **Before/After 比例严重失衡**：fullpage 2300–2900 段，AFTER cell 由于 mermaid 自动布局
  渲染出一个**横向且紧凑**的图（5 节点单链），而 BEFORE cell 是垂直多分支（5 分支扇形）。
  两个 cell `align-items: stretch` 强制等高 = AFTER cell **底部 60% 完全是空白
  cream 背景**。这是整页最刺眼的视觉问题。
  - 修：在 `.flow-cell .mermaid` 上加 `min-height: 100%; display: flex;
    align-items: center; justify-content: center;`，让 AFTER 的图垂直居中。
    或者把 flow-grid 的 `align-items: stretch` 改成 `align-items: start`，
    AFTER cell 自然缩短到 fit-content，让两个 cell 高度不等但都"紧凑"——cream
    背景在两 cell 间空一段比 cell 内部空一段视觉舒服很多。
  - 进一步可以在 AFTER cell 内加一行 italic Fraunces caption（如 "5 source kinds
    → 1 dispatcher"）填补底部，顺带强化"对照"叙事。
- **Risk Snapshot → Architecture 之间的过空**：见 §3，~136px 的 margin 累加是
  全页最稀疏的位置，但内容上是从"风险"切到"图"，主题跳跃。把 risk-snapshot
  并入 TL;DR section 内，能同时解决间距和主题切换两个问题。
- 其他 section 节奏均匀，5500–5800 总高度可以承受，不显空。

---

## 如果只能再改 3 处视觉

1. **修 After flow cell 的 60% 空白** —— `.flow-cell { align-items: center }` +
   `.flow-grid { align-items: start }`，让 AFTER 高度自适应而非被拉到与 BEFORE 等高。
   这是当前最刺眼的视觉残缺，比任何 chip 调字号都重要。
2. **解决 Architecture summary 与 hero subtitle 的 italic 撞角色** —— summary 改
   upright Inter 17px + mono eyebrow ("概览 ·")，把 italic 这张牌留给 caption / cost /
   question 三处装饰角色。让 hierarchy 清晰，hero subtitle 也因此更独占。
3. **统一圆角语言** —— `.risk-snapshot .pill { border-radius: 2px }`，
   消除整页唯一的圆角元素。同时把 `.word` 的 italic 改 mono——让 risk-snapshot
   从"chip 异域风"回归到全站的"印刷品 + monospace 数据" 美学。

附带（不算 3 处但顺手）：删 `.decisions-meta` 那条信息冗余的小灰字。
