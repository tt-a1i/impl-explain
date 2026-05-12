# impl-explain v2 视觉评审

评审范围：6 张视口截图 + `scripts/render.py` 内嵌 CSS / Mermaid theme。
评审目标：保持单文件 HTML、不引入新字体/新 JS、不重构 HTML，仅在 CSS 变量、字号、spacing、颜色层面给出可落地改动。

---

## 1. 整体视觉风格统一性

**P0 ｜ 白色卡片把杂志风打断成 dashboard。**
`--bg-card: #ffffff` 直接坐在 `--bg: #faf7f2` 上（截图 2 的 architecture、截图 5 的 before/after、`diagram-wrap` 与 `flow-cell` 全部命中），形成一块毫无温度的纯白矩形——这是当前页面唯一一处"工程文档"气质的入侵。
改动：`--bg-card: #fdfaf3`（或直接复用 `--bg-soft: #f5f0e7`，让卡片陷下去一点而不是浮起来）。同步把 `JS` 里 `themeVariables.background` 从 `'#ffffff'` 改成 `'#fdfaf3'`，`primaryTextColor` 保持 `#1f1c17`。

**P0 ｜ Mermaid 节点底色和卡片底色脱钩。**
Mermaid `primaryColor: '#fbeede'`（accent-soft，米色偏粉）+ `secondaryColor: '#f5f0e7'` 在白卡上还能看，一旦卡片变奶油色就会糊成一团。把 `secondaryColor` 改成 `'#ffffff'`（普通节点用白底 + `nodeBorder: '#d6cdba'` 描边），让被高亮的"新增"节点（`#fbeede`）继续保留对比度。

**P1 ｜ flow-cell 比 diagram-wrap 紧 16px，节奏不一致。**
`diagram-wrap` 用 `padding: 40px 32px`，`flow-cell` 用 `24px 20px`，但二者承担同一角色（包裹 mermaid）。把 `flow-cell` 改成 `padding: 32px 24px`，并把 `flow-grid` 的 `gap: 20px` 提到 `28px`，让 before/after 像两张"半页配图"而不是两张缩略图。

**P2 ｜ `border-radius: 4px` 在卡片和 chosen-line 上都偏 UI 化。**
杂志风的圆角应该接近 0 或 ≥10px。建议 `diagram-wrap` / `flow-cell` 全部改 `border-radius: 2px`，`.decision .chosen-line` 也跟到 `2px`，去掉那点"按钮感"。

---

## 2. 排版

**P0 ｜ 决策序号 01–06 在 36px / `--text-faint` 中间地带，既不装饰也不引导。**
当前 `font-size: 36px; color: var(--text-faint)`（#b8b0a0）几乎看不见。杂志页码风要么大要么实。建议：`font-size: 56px; line-height: 1; color: var(--rule)` （#ede5d3，再淡一档但更大）；并把 `.decision` 的 `grid-template-columns` 从 `60px 1fr` 提到 `88px 1fr`、`gap: 24px` 提到 `32px`。

**P1 ｜ Rejected 与 Cost 两条 italic Fraunces 小字撞角色。**
截图 3/4 里 `.rejected-line` 是 italic 13px text-muted、`.cost` 是 italic 14px text-muted，眼睛读不出层级。让 `.rejected-line` 换成 Inter 13px upright（去掉 `font-style: italic`，加 `font-family: 'Inter', sans-serif`），把"放弃"作为列表事实；`.cost` 维持 italic Fraunces 作为反思短句。

**P1 ｜ letter-spacing 没有体系，七处 mono 标签从 0.12em 散到 0.32em。**
建议收成三档并贴在场景上：
- 0.12em — 长串路径 / 元数据（`.report-meta`、footer）
- 0.16em — 行内小标签（`.tag`, `.rl-label`, `.mit`, `.sev`, `.cost::before`）
- 0.22em — 区段 eyebrow（`.eyebrow`, `.flow-label`, `.tldr-block .label`）
当前 `h2.section-title` 的 0.32em + Fraunces 13px 偏紧绷，建议降到 `0.26em`。

**P2 ｜ Hero 副标题 Fraunces italic 22px 与 TL;DR body Fraunces 22px 字号相同。**
两处都是入口级 serif，眼睛分不出"副标题"和"摘要正文"。把 `.report-subtitle` 提到 `font-size: 26px; line-height: 1.4`，并把 `max-width` 从 600px 收到 520px，让它更像 dek。

**P2 ｜ `.decision .question` 24px 与 `.tldr-block .body` 22px 在视觉上压不住决策卡。**
决策的问句应该是最重的次级 voice。建议 `.question` 提到 `font-size: 27px; line-height: 1.3; font-weight: 500`，并把下方 margin `0 0 20px` 收到 `0 0 16px`。

---

## 3. 颜色与状态

**P0 ｜ `--chosen` 是页面上唯一的冷色，与 terracotta 系打架。**
`#2f6e3f` 和 `#e7f0e6` 在暖色调里发蓝。建议向橄榄/苔藓偏：`--chosen: #4a6a2c`，`--chosen-soft: #ecefd9`。这样三种状态色（terracotta accent、olive chosen、ochre deferred、burnt rejected）落在同一个暖色色相环上。

**P1 ｜ `--rejected` 与 `--accent` 都是红橙系，相互削弱。**
Accent `#b04a1f` 已经是 terracotta，`--rejected: #98352c` 与它 hue 差 ~10°，截图 6 里 HIGH 标签和 hero 上的 eyebrow 圆点是同一种"红"。把 `--rejected` 改深一档冷红：`#7a2f24`，`--rejected-soft: #f1ddd5`。让"被拒"读起来更像"压抑"，而不是"二次强调"。

**P1 ｜ Risk severity 中的 LOW 颜色和正文 muted 撞色。**
`.risk-row.sev-low .sev` 用 `--text-muted: #8a8275`，与 `.desc .note` 颜色一致，导致"LOW" tag 读起来不像 tag 而像注脚的延伸。建议 LOW 单独用 `#a89970`（暖灰偏黄），保留 tag 的辨识度但仍然是低权重。

**P2 ｜ chosen-line 当前是"色条 + 浅底"，rejected/deferred 状态共用结构但语义弱。**
绝大多数决策都是 `status: chosen`（看 input），导致 deferred / rejected 的色条永远不出现。建议把 `.decision .chosen-line` 的 `border-left: 3px` 加粗到 `4px` 并改成 `border-radius: 0`，让色条变成更明显的"杂志引言竖线"。

---

## 4. 空间与节奏

**P1 ｜ section 96px 间距 + section-title 后 40px 在 Hero → TL;DR 这段过空。**
截图 1 末端到截图 2 开端可以看到，副标题 + meta + section-title 之间有 56px + 96px + 40px ≈ 三段空白叠加。建议 `section { margin: 80px 0 0; }`，`h2.section-title { margin: 0 0 32px; }`，并把 hero `.report-meta { padding-top: 24px }` 提到 `32px` 让 meta 自己呼吸而不是被 section gap 顶。

**P1 ｜ Decisions 之间 56px gap 偏紧。**
6 张决策卡的视觉权重很高（标题 + 色条 + 三行小字），56px 让它们叠在一起像列表。建议 `.decisions { gap: 72px; }`，并在 `.decision::after` 加一条 `content: ''; display: block; width: 32px; height: 1px; background: var(--rule); margin-top: 32px;` 作为决策之间的轻分隔（最后一个用 `:last-child::after { display: none; }`）。

**P2 ｜ tldr-block 标签列 92px 偏窄，"目标 / 方案 / 权衡" 在 11px mono 下贴边。**
建议 `.tldr-block { grid-template-columns: 112px 1fr; gap: 32px; }`，让标签列与正文之间产生明显的"边栏感"。

**P2 ｜ 整页 `max-width: 760px` 对架构图过窄。**
（这一条只建议给 mermaid 卡片解锁宽度，文字保持 760px）：`.diagram-wrap, .flow-section .flow-grid { max-width: 920px; margin-left: -80px; margin-right: -80px; }`，让两张图突破阅读栏，文字部分继续保留杂志栏宽。

---

## 5. Mermaid 图融入度

**P0 ｜ 节点字号 13px 在 760px 内的复杂 flowchart 上读不清。**
截图 2 的 architecture 节点字几乎要凑到屏幕看。把 `themeVariables.fontSize: '13px'` 提到 `'14px'`；同时把 `flowchart.padding: 20` 降到 `12`，让节点之间的连线不被过大留白稀释。

**P1 ｜ 高亮"新增"组件的 `#fbeede + #b04a1f` 与普通节点对比度刚好够。**
但 `lineColor: '#8a8275'` 是中性灰，导致 terracotta 描边的高亮节点的连线和其他节点的连线毫无区别。建议 `lineColor: '#a89685'`（更暖更淡），让 terracotta 描边在连线之上自然跳出。

**P1 ｜ before / after 标签当前是 `.flow-label`（mono 10px 0.22em），before 是 muted、after 是 chosen 绿。**
现在 chosen 改 olive 后这条标签会自动协调；额外建议把 `.flow-cell.before .flow-label { color: var(--accent); }` —— before 用 terracotta、after 用 olive，形成 "旧 / 新" 的对仗色，而不是 "灰 / 绿" 的非对称。

**P2 ｜ `clusterBkg: '#faf7f2'` 和页面背景同色，subgraph 边框 `#e9e3d8` 在 cluster 内几乎消失。**
建议 `clusterBkg: '#f5f0e7'`（bg-soft），让 cluster 自己微微下沉，可读性上来。

---

## 6. 细节

**P1 ｜ Out of Scope 的 `×` 标记是页面唯一的"checkbox UI"残留。**
JetBrains Mono 14px × 配 italic Fraunces 在编辑页面里像 todo 应用。建议改成 em-dash 前缀：`content: '—'; color: var(--text-faint); font-family: 'Fraunces', serif; font-size: 16px; left: 0; top: 0;`，并把 `.oos-list li { padding-left: 28px; }`。整列读起来变成"被划掉的小节"。

**P1 ｜ Eyebrow 上的 `.dot` 与 footer 上的 `.end-mark` 是同一个 terracotta 圆点。**
现在 eyebrow dot 5px、end-mark 8px，没有明显呼应。建议把两者绑成"开篇 / 收尾"对偶：eyebrow dot 改成 `width: 6px; height: 6px;`，end-mark 改成 `width: 6px; height: 6px;`，让首尾构成同尺寸的"句点"。

**P2 ｜ `.cost::before { content: '代价 — '; }` 中文破折号位置贴得太紧。**
当前 `margin-right: 8px` 在 italic Fraunces 14px 旁边读起来像连字。改成 `content: '代价'; margin-right: 12px; padding-right: 10px; border-right: 1px solid var(--rule);`——用一道发丝竖线代替破折号，跟全文的发丝分隔风格统一。

**P2 ｜ `.report-meta` 两列 `key`/`val` 中间 8px 太挤，特别是 plan 路径很长时。**
改 `margin-right: 12px` 并给 `.item` 加 `display: inline-flex; align-items: baseline;`，避免长路径换行时 key 飞掉。

**P2 ｜ section-title 横线在 16px gap 后才接上，标题与线之间能看到"接口"。**
建议把 gap 从 `16px` 提到 `24px`，并把 `::after` 的 `height` 从 `1px` 降到 `0.5px`（视网膜下半像素），让那条线更像底纹。

---

## 如果只能改 3 处

1. **`--bg-card: #fdfaf3` + mermaid `themeVariables.background: '#fdfaf3'`** — 消除全页唯一的 dashboard 白卡，把 architecture / before-after 两张图重新拉进杂志色温里。这是当前最大的风格断点。
2. **`--chosen: #4a6a2c` / `--chosen-soft: #ecefd9`** — 把唯一的冷色调状态色迁到橄榄绿，让 terracotta / olive / ochre / burnt 四种状态色全部落在暖色色相环内，整页色味一次性收敛。
3. **决策序号 `font-size: 56px; color: var(--rule);` + `.decision` 网格列宽 `88px 1fr` / gap `32px`** — 把 01–06 真正做成杂志页码式装饰，决策卡之间的视觉骨架立刻立得起来，比任何 spacing 微调都直接见效。
