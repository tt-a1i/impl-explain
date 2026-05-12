---
name: impl-explain
description: 在用户已经完成一次 implementation 工作后，把项目里的 implementation plan + git diff/log 渲染成一份单文件 HTML 实施报告。报告包含 TL;DR、风险概览、架构图（mermaid）、Before/After 数据流、决策记录卡片、风险清单。用于开会前快速对齐团队、向 reviewer 解释设计决策、归档实施叙事。当用户说"生成实施报告"、"impl-explain"、"explain implementation"、"展示这次实施方案"、"做一份 HTML 实施总结"时调用本 skill。
---

# impl-explain

## 用途

把一次实施任务的方案叙事整理成单文件 HTML 报告。**代码细节不在范围内**（reviewer 想看 diff 自己 `git diff`），重点是**为什么这么做、考虑过什么、放弃了什么、留了什么坑**——这些信息只存在于实施当时，错过就丢了。

## 触发时机

仅在用户已经**完成一次实施**且希望生成可视化总结时调用。如果用户只是闲聊或实施还没做完，不要 auto-invoke。

## 执行步骤

### 1. 找 plan 文件

按优先级查找：

1. **用户指定路径**：必须做安全校验——位于 `git rev-parse --show-toplevel` 之内，不得匹配 `.env*` / `*.pem` / `*.key` / `id_rsa*` / `credentials*` 等敏感模式，不得含 `..` 段。任一不符合：停下来告诉用户并拒绝。
2. `docs/superpowers/plans/` 下日期最新的 `.md`
3. `docs/plans/` 下日期最新的 `.md`
4. 项目根目录下符合 `*plan*.md` 模式的最新文件

**多 plan 仓库交叉验证**：如果目录里 > 1 个 plan，"日期最新"不够准。算法：

- 跑 `git log <base>..HEAD --format='%s%n%b'` 收集 commit token set（按非字母数字切分，过滤停用词 + boilerplate 如 `superpowers/tracking/plan/implementation`，过滤长度 ≤ 2 + 纯数字）
- 每个 plan 取**特征段落**（文件名去日期 + h1 + `## TL;DR` 段 + `## Decisions` 的 `###` 子标题）按同规则切 token
- overlap = |commit_tokens ∩ plan_tokens|；**top1 - top2 ≥ 3 且 top1 ≥ 5** 才自动选，否则**问用户**

找不到任何 plan：告诉用户先写一份再跑，停止。

### 2. 收集 git 上下文

- base 分支：`git symbolic-ref refs/remotes/origin/HEAD --short` 失败则 fallback `main` → `master`
- commits：`git log <base>..HEAD --format='%h %s' --no-merges`
  - 输出为空（分支已 merge）：`git log -10 --no-merges` 取最近，**让用户确认**哪几条属本次
  - 超 30 条：压缩成 `"<first> .. <last> (N commits)"` 一行
- 改动文件：`git diff <base>..HEAD --name-status`（**只用来理解范围，不嵌进 HTML**）

### 3. 直接写 HTML

不需要中间 JSON，不需要外部脚本，直接生成单文件 HTML 写到 `git rev-parse --show-toplevel` / `impl-explain.html`（不在 git repo 时落 CWD 并显式告诉用户位置）。

**视觉参考**：本 skill 目录下的 `examples/sample.html` 是一个完整渲染好的样例。

**硬约束（必读 + 必做）**：

1. **完整读 sample.html**——不要扫前 200 行就走。重点确认你拿到了完整的 `<style>` 块、`<script>` 块、以及顶部 sticky TOC / progress bar / hero / TL;DR-risk-tail / decision card / risk-snapshot / risk-highlight / out-of-scope 这 8 个结构片段
2. **CSS / JS 整段 verbatim 复制**——把 sample.html 里的 `<style>...</style>` 和 `<script>...</script>` 整段原封不动拷到你生成的 HTML，**只改 `<body>` 里的内容**。不要尝试"挑出几个色 token 自己写 CSS"——团队跨报告一致性 > 单次创意。换风格的方式是单独换 sample.html，不是每次 freestyle
3. **mermaid 安全 shim 必须出现**——下面这段 JS 必须出现在你的 `<script>` 块开头（mermaid.initialize 之前），sample.html 里已经有，你按上一条 verbatim 复制就自动带过来；但你单独检查一遍：

```javascript
// 安全前导：data-content 里 mermaid 源是 HTML-escaped 的，先 textContent 解码再交给 mermaid
(function () {
  document.querySelectorAll('.mermaid[data-content]').forEach(function (el) {
    el.textContent = el.dataset.content;
    el.removeAttribute('data-content');
  });
})();
```

漏掉这 8 行 + 配套 `htmlLabels:false` = mermaid 节点 label 里的 `<script>` / `<img onerror>` 直接 XSS。这是 v1 修过的真实 P0 安全漏洞，v2 lite 不能 regress。

4. **mermaid 字符串必须 HTML-escape 后存到 `data-content` 属性**——具体形式：

```html
<div class="mermaid" data-content="flowchart LR&#10;  A --&gt; B&#10;  classDef newcomp fill:#fbeede&#10;  class A newcomp"></div>
```

**不要**直接 `<div class="mermaid">flowchart LR ...</div>` 把源码塞进 innerHTML。

**写入方式**：先写临时文件再 rename（原子写入），避免中断时留半成品 HTML。

### 4. 报告输出路径给用户

告诉用户绝对路径 + 简短摘要（N decisions / N risks / N high）+ "双击即可在浏览器查看"。

---

## 报告应有的结构

下面的段不必都出现——**plan 里没素材就跳过整段**，不要硬凑节点 / commit list / 文件清单充数。叙事密度 > 信息覆盖度。

### Hero
- 大号 Fraunces 衬线标题（实施名）
- 一句话 italic 副标题
- 可选 1-3 个 metric chip（最有量级感的数字，如 `47 → 1 loops`、`4 sources unified`）。**不要堆 6/5 这种 decisions/risks 计数 chip**——那是 section meta 的事
- plan 文件路径 + commits 列表（超 3 条折叠"展开 N commits"）

### TL;DR
三行：**做什么 / 怎么做 / 代价**。

- "代价" 必须是**整体账**（"换走 47 个 loop 复杂度，引入调度器单点"），**不复述某条 Decision 的局部 cost**
- 三句念给没看过 plan 的同事听，30 秒能让对方理解大致在做啥——做不到就重写
- TL;DR 尾接一行风险预告 + → Risks 锚跳（如 `5 risks · 1 high (已缓解) · 看详情 →`）

### Architecture
- mermaid flowchart 节点 ≥ 5
- **新组件用 `classDef newcomp fill:#fbeede,stroke:#b04a1f,color:#1f1c17,stroke-width:1.5px` + `class A,B,C newcomp` 高亮**
- **不要**写 `style X fill:#暗色`——会跟浅色主题打架
- 图上方可选一行 mono "叙述"标 + Inter upright 16px 描述图意；图下方可选 italic 14px caption 说明颜色/箭头编码

### Before / After（可选，只在数据流真改变时放）
两张并排 mermaid。**`flowchart TB` 通常比 `LR` 排版更稳**（cell 高度更均衡）。

### Decisions
- 编号卡片（01-NN），**标题是结论式短句**（"集中注册表放 cadence"），不是问号长句
- 每张：`chosen`（采用一句话）/ `rationale`（理由 2-4 句）/ `rejected`（放弃的备选 list）/ `cost`（局部代价）/ `status`（`chosen` 或 `deferred`——**没有 `rejected`**，被全否决的决策放进 Out of Scope）
- 建议 3-8 条，挑"反过来选会出大问题"的关键决策。鸡毛蒜皮不进

### Risks
- 顶部 snapshot 行：`5 risks · 1 high · 2 medium · 2 low`
- 紧跟一行 inline "Top risk" 卡（取最高 severity 未缓解的那条，背景按 severity 染色）
- 完整列表：每条 `severity` (low/medium/high) + `description` + 可选 italic `note` + `mitigation` (full/partial/none) 标签

**mitigation 同义词速查**（避免误判）：
- `partial`：note 含 future / 后续 / 后期 / 长期 / TODO / 暂未 / 未接入 / 上线后 / 已沉淀 / 需补
- `none`：未做 / 尚未观测 / 未来加 / 计划中 / 暂时不做 / 待+动词（待评估 / 待补充）
- `full`：note 描述**已经生效**的具体阻断机制（启动校验、测试覆盖、flag 判断）
- 拿不准倾向写 `partial`，比 `full` 更诚实

至少 1 条（`validate` 不再做硬卡，但 0 风险报告通常不真实——多副本部署 / 第三方依赖 / 静默失败 三类至少能想到一类）

### Out of Scope
故意没做的事，italic 列表。具体（"暂未做 leader election"）而非空泛（"未来可能优化"）。

---

## 视觉规范

**唯一规则：完整 verbatim 复制 sample.html 的 `<style>` 和 `<script>` 块。**

不要"挑几个 token 自己写"，不要"按记忆里 v1 的样子重写"，不要"加点新风格"——agent 没有"风格设计权"，只有"内容生成权"。换视觉只能改 sample.html 一份文件，从而让所有未来报告同步变。

下表只用来快速核对你复制过去的 CSS 还能找到这些 token（不是让你单独定义）：

```
背景:    --bg #faf7f2 (warm cream)  / --bg-card #fdfaf3
文字:    --text #1f1c17  / --text-soft #4a443a  / --text-muted #8a8275  / --text-faint #b8b0a0
强调:    --accent #b04a1f (terracotta)
状态:    --chosen #4a6a2c (olive)  / --deferred #8a5a17  / --rejected #7a2f24
severity: high #7a2f24  / medium #8a5a17  / low #a89970
mit:    full #4a6a2c  / partial #8a5a17  / none #b8b0a0
字体:    Fraunces (serif 标题) + Inter (正文) + JetBrains Mono (label) — Google Fonts CDN
mermaid: theme 'base' + 上面 token / fontSize 14 / htmlLabels: false
布局:    max-width 760px, padding 64px 32px 120px, sticky TOC + 1px progress bar
```

如果你复制过去的 CSS 找不到上面任一 token，说明你没读完 sample.html——回去重读。

---

## 安全约束（必读）

- mermaid 源字符串可能含 LLM 生成的恶意标签。**写入 HTML 前**：
  - mermaid 配置必须 `htmlLabels: false`（节点 label 渲染为 SVG `<text>`）
  - 把 mermaid 源放进 `<div class="mermaid" data-content="ESCAPED"></div>` 的 attribute 而不是直接 innerHTML，加一段 JS shim 在 `mermaid.initialize()` 前用 `el.textContent = el.dataset.content` 复制回来
  - data-content 的值必须**完整 HTML escape**（`&` `<` `>` `"` `'`）
  - 不写 `<script>` `<iframe>` `<object>` 等危险标签到 mermaid 字符串里
- 一次性原子写入：先 tmpfile，rename 替换目标
- HTML 输出**默认不 commit**（在 .gitignore 里加 `/impl-explain.html` 或让用户自己决定）

---

## 不要做的事

- **不嵌 git diff 内容**——HTML 是叙事不是 changelog
- **不加文件清单段**——reviewer 自己 `git diff --name-status`
- **不自创视觉风格**——读 sample.html，抄它
- **plan 信息薄弱时不靠加节点 / 加 commit list 充数**——叙事密度 > 信息覆盖度；信息真不够就停下来问用户
- **不把 HTML 输出到 git repo 的源码目录**造成噪声——默认输到项目根，让用户自己决定 commit 否
