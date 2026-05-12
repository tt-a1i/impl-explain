# impl-explain SKILL.md / JSON schema 可执行性评估

日期：2026-05-11
评估视角：被 `/impl-explain` 触发后从零开始读 SKILL.md 的 LLM agent
评估目标：SKILL.md 步骤指令、JSON schema 字段设计、跨家可移植性、与 plan 模板的契合度、agent 真实生成时的失败模式

---

## 1. SKILL.md 指令清晰度

### 1.1 步骤 1（定位 plan 文件）—— P0 风险点

目前指令是"`docs/superpowers/plans/` 下日期最新的 `.md`"。在 `global-hotspot-globe` 仓库实测：该目录下有 **8 个 plan**（看 git status 里就有一个 `2026-05-09-new-pulse-source-review.md`），且文件名都以日期开头。agent 会怎么选？

- 字典序最新 ≠ 这次实施对应的 plan。比如 PoC 分支做的是"normalizer"，但 `docs/superpowers/plans/` 里日期最新的可能是另一条线的 plan。
- 没有用 git 当前分支名 / commit body 关键词去交叉验证。

**改法**：步骤 1 改为"先取 `git log <base>..HEAD --format=%s%n%b` 收集本次实施所有 commit subject + body 的关键词；再列 `docs/superpowers/plans/*.md`，按文件名/标题与关键词的重合度排序；若 top1 与 top2 重合度差 < 2 个关键词，**问用户哪个**而不是猜"。同时把"日期最新"作为兜底（P0）。

### 1.2 步骤 3（字段质量要求）—— P1 高跳过率

"字段质量要求"这段写得很好，但放在一大段 JSON schema 后面，agent 在做"先把 JSON 写出来"的紧迫感下**大概率扫一眼就跳过**。typical AI 行为：先生成 JSON 把脚本跑通拿绿灯，再回头补质量——但 8 成情况不会回头。

**改法**（P1）：把"TL;DR 三句必须 30 秒讲完"、"决策最少 3 条"、"风险至少 2-3 条"这些**硬约束**直接写进 schema 的 `description` 字段，让 validator 在数量上做最低门槛检查（见 §3.6）；不能 schema 化的（如"不要堆术语"）放在每个字段的注释紧邻处，而不是统一聚到段尾。

### 1.3 "不要做的事" —— P2

写得够具体（不嵌 diff、不改 HTML、不编造决策、不塞额外字段、不输出到源码目录、不用暗色 mermaid style），覆盖面 OK。但**最后一条"不要在 mermaid 里写暗色 style"已经在步骤 3 里说过了，重复**——agent 看到重复信息容易判断"前面那段不重要 because 后面又说一遍"。

**改法**（P2）：删掉"不要做的事"的最后一条，只在步骤 3 的架构图字段处说一次；或者反过来步骤 3 只点一下"避免暗色 style，详见末尾禁忌"。

### 1.4 隐含知识盘点

- "main 或 master，看哪个存在" —— agent 会 `git rev-parse --verify` 还是 `git branch -a | grep`？没说。三家 agent 行为可能不一致。**改法**（P2）：明确建议 `git symbolic-ref refs/remotes/origin/HEAD` 拿默认分支，fallback `main` → `master`。
- "调用 scripts/render.py" 但没说**用什么 Python**。某些环境 `python` ≠ `python3`。SKILL.md 步骤 5 写的是 `python3`，OK，但应明确"若 `python3` 不存在，尝试 `python --version` 确认 ≥3.8"。
- 步骤 4 给了两个临时文件位置（`/tmp/...` 和 `.impl-explain.input.json`），没给选择标准。agent 会随机挑。**改法**（P2）：明确"优先 `/tmp/`；如果 `/tmp` 不可写（罕见，但 Codex 沙箱可能限制）回落到项目根 + `.gitignore` 提示"。

---

## 2. 跨家可移植性

### 2.1 Claude 专属占位符 —— 当前是干净的（P0 通过）

grep 全文：没有 `${CLAUDE_SKILL_DIR}`、`$ARGUMENTS`、`` !`cmd` ``。指令也是叙事化的（"找到 plan"、"运行 git"），不点名 Read/Bash。这一条调研报告的 §5.4 要求被遵守了。

### 2.2 步骤 5"agent 自己拼脚本路径" —— P0 改进点

目前的兜底列表只列了 4 处，加 `find ~ -path '*/impl-explain/scripts/render.py'`。三家行为：

- **Claude Code**：理论上 agent 可以从环境推断 `${CLAUDE_SKILL_DIR}`（但 SKILL.md 没让用），实际 agent 会先按你的列表第一条 `~/.claude/skills/impl-explain/...` 命中。OK。
- **Codex**：在沙箱里执行 shell。`~/.codex/.agents/skills/...` 在你的列表里，OK；但**沙箱可能不允许 `find ~`** 全盘扫，会超时或被拒。
- **opencode**：`~/.config/opencode/skills/...` 在列表里，OK；但若用户 `install.sh` 把 skill 装到 `~/.agents/skills/` 而非 `~/.config/opencode/skills/`，opencode 仍然能扫到 SKILL.md（调研报告 §1 说 opencode 也读 `~/.claude/skills`、`~/.agents/skills`），但你的兜底列表**没列 `~/.agents/skills/impl-explain/...`**——这是调研报告 §5.2 推荐的安装位置，遗漏了。

**最易失败**：Codex 沙箱跑 `find ~`。

**改法**（P0）：兜底列表加 `~/.agents/skills/impl-explain/scripts/render.py`；并改"`find ~ ...`"为"先 `dirname` 当前 SKILL.md 所在路径（agent 在多数 agent 里能拿到）+ `/scripts/render.py`"，把 `find` 作为最后手段。三家中 Claude Code / Codex 都会把 SKILL.md 的路径传给 agent 上下文，让 agent 用 `dirname` 比满盘 find 稳。

### 2.3 description 字符 / 触发词 —— P1

数了下当前 description：约 230 中文字符（≈ 690 字节）。在 Codex 8000 字符上限 / opencode 1024 字符上限内，**OK**。

触发词分布：
- 前 100 字节："在一次 implementation 工作完成后…HTML 实施报告"——关键词 implementation / HTML report 都在前 200 字符。✓
- 后半"当用户说 …"列了 5 个触发短语，3 中 2 英。✓

**问题**：调研报告 §6.7 说 Codex `/skills` 菜单**对 description 截断阈值更严**。当前 description 后半段的触发短语放得有点远，Codex 用户看菜单时可能看不到中文触发短语。

**改法**（P1）：把触发短语前移；句式压成"… 用于开会前对齐团队、向 reviewer 解释决策、归档实施叙事。触发：'生成实施报告' / 'impl-explain' / 'explain implementation' / '把 PR 画成 HTML'"。

---

## 3. JSON schema 设计

### 3.1 `decisions[].status` 三态语义自洽性 —— P0 模糊

当前三态：`chosen` / `rejected` / `deferred`。模板和示例只用了 `chosen` 和 `deferred`。

**问题**：`status="rejected"` 的整个 decision 出现在报告里**语义混乱**——decision 的 `chosen` 字段已经写了"最终选择"，再来一个 `rejected` status 就是"决策本身被否决了"，那它为什么出现在最终报告？render.py 的 CSS 给 `.decision.status-rejected .chosen-line` 红色背景，仿佛是合法状态，但 SKILL.md 没教 agent 什么场景下用。

**改法**（P0，二选一）：
- 选 A：删掉 `rejected` 状态。`status` 只剩 `chosen` / `deferred`（已决定 / 推迟）。简单且无歧义。
- 选 B：保留三态但 SKILL.md 明确说明"`rejected` = 实施期间曾考虑此问题、但**整个决策（包括所有备选）都不做**"。这种情况罕见，多数时候是 out_of_scope 该装的内容。建议选 A。

### 3.2 `risks[].mitigated` 二态 vs 三态 —— P1

二态 `bool` 简单，但调研显示真实风险常常是"部分缓解"。当前示例 risk #4（"单 source 失败被吞掉只 log warning"）`mitigated: true`，但 note 里写"future 接 Prometheus / Sentry"——很明显是**部分缓解**。

**改法**（P1）：改成 `mitigation: "full" | "partial" | "none"`（字符串三态，避免 bool 升级到三态时跟旧数据冲突）。render.py 渲染时三色：full=绿 / partial=黄 / none=灰。SKILL.md 步骤 3 增加一句"如果 note 里出现'future'、'后续'、'暂未接入'等字样，多半是 partial 而非 full"。

### 3.3 `meta.git_range` —— P1 重写场景常错

当前是字符串 `"main..codex/agent-normalizer-poc"`。两个常见场景会失效：

- **场景 (b)**（评估提示中）：分支已 merge、main 已 fast-forward 后，`main..HEAD` 返回空，但报告还想生成。agent 此时填 `"main..HEAD"` 会让读者困惑。
- **场景**：用户在中间分支跑（feature 分支 fork 出 sub-feature），`main..HEAD` 包含上游别人的 commit。

**改法**（P1）：把 `git_range` 改成 **`commits: list[str]`**（一组 short SHA 或 subject），让 agent 显式列本次实施相关的 commit。报告渲染时显示为一个紧凑列表。SKILL.md 步骤 2 加：

> 优先用 `git log <base>..HEAD --format='%h %s' --no-merges`；如果输出为空（已合并），改用 reflog 或 cherry-pick 范围；如果列表 > 30 条，可压缩成"<short SHA> .. <short SHA> (N commits)"字符串。

兼容方案：保留 `git_range` 兜底，新增 `commits` 优先取。

### 3.4 `architecture_diagram.caption` —— P2

模板里完全没出现 `caption`，demo input 也没填。agent 99% 不会主动填。

**改法**（P2）：要么删掉 caption 字段（保持 schema 紧凑），要么在 plan-template.md 的 Architecture 段加一行"在 mermaid 块后用 `> Caption: <一句话>` 标记 caption，agent 会提取"——让 plan 作者有触发机会。建议删掉，少一个 agent 困惑点。

### 3.5 `decisions[].rejected` 为 `list[str]` —— P2 略松

只要求 list of string，但语义上每个 rejected 也是"备选方案 + 不选的理由"。当前只让填方案名，理由被合并进总 rationale。**实际效果**：示例里 rationale 经常变成"为什么不选 A、不选 B、为什么选 C"杂糅。

**改法**（P2，可选）：升级成 `list[str] | list[{name: str, why_not: str}]`，让 render.py 检测元素类型。如果是 dict 形式，渲染 "不选 X，因为 Y"。但这会增加 schema 复杂度；保持 list[str] 也可，靠"字段质量要求"约束 rationale 写法。**保留现状 + 强化约束**更现实。

### 3.6 缺失"数量下限"约束 —— P0

`validate()` 函数：`decisions = data.get("decisions") or []`，允许空。同样 risks 也允许空。这跟 SKILL.md 的"最少 3 条决策、至少 2-3 条风险"硬约束矛盾——agent 写 0 条也能过。

**改法**（P0）：`validate()` 加：
- `len(decisions) >= 1`（强制至少 1 条，否则不是"实施报告"了）；warn 但不 fail when `< 3`
- `len(risks) >= 1` 同上
- 不强制 architecture / data_flow（这俩本来是 optional）

错误信息要带上 SKILL.md 的指引文本，比如"decisions 为空——请补充至少 3 条关键决策；'无决策'通常是漏读了 plan 的 ## Decisions 段。"

---

## 4. 与 plan-template.md 的契合度

逐段对照：

| Plan 段 | JSON 字段 | 契合度 |
|---|---|---|
| TL;DR（3 项 bullet） | `tldr.{goal, approach, tradeoff}` | ✓ 完全对应 |
| Architecture（叙述 + mermaid） | `architecture_diagram.{type, diagram}` | ✓ 但叙述部分丢了（mermaid 上方的 2-3 句话没字段装），可考虑增加 `architecture_diagram.summary` |
| Data Flow（Before/After mermaid） | `data_flow.{before, after}` | ✓ |
| Decisions（Chosen / Rejected / Rationale / Cost / Status） | `decisions[]` | ✓ 字段名一致 |
| Risks（severity / mitigated / note） | `risks[]` | ✓ |
| Out of Scope | `out_of_scope[]` | ✓ |
| Tasks | （无） | ✓ 明确说不进报告 |

**Gap 1**（P2）：Architecture 段的"2-3 句话描述"在 JSON 里无处可放。agent 会塞进 caption（缺乏触发）或丢弃。**改法**：加 `architecture_diagram.summary: str | None`，模板里把"2-3 句话描述"对应到 summary。

**Gap 2**（P1）：模板 Risks 写法是行内 markdown `**X** — severity: high — mitigated: yes`。agent 要把这种"行内 metadata"解析成结构化字段，对 LLM 来说不难，但**模板里没给反例提示"如果你直接 copy plan 的字符串当 description，会把整行 metadata 当描述带进去"**。建议模板加一行"agent 提取时，把 `— severity` 之前的部分作为 description"。

---

## 5. agent 真实生成 JSON 时的失败模式

### 5.1 场景 (a)：plan 烂，`## Decisions` 段缺失

当前 SKILL.md "输入数据来源优先级"段已经覆盖：plan → 对话历史 → commit message → 代码。**这段写得对**，但 agent 容易**直接跳到第 4 步（从代码推断）**而忘记问用户。

**改法**（P1）：在该段加硬约束："如果 plan 没 `## Decisions`，**先 grep commit body 找 'why' / 'because' / '考虑过' 关键词**；如果还是不够 3 条，**停下来问用户**'plan 里没记录决策，要不要口头补几条？'。不要 silently 从代码瞎猜。"

### 5.2 场景 (b)：分支已合并，`git log main..HEAD` 返回空

当前 SKILL.md 没覆盖。agent 会得到空字符串当 `git_range`，validator 会过（meta.git_range 只要求 str），但报告里这字段会显示空。

**改法**（P1）：步骤 2 加"如果 `git log <base>..HEAD` 返回空，尝试 `git log -10 --no-merges` 取最近 10 条 commit，让用户确认哪几条属于本次实施"。配合 §3.3 改成 `commits: list[str]`，这场景就自然 resolve 了。

### 5.3 场景 (c)：plan 里架构图是 ASCII art

agent 行为两种：
- 直接把 ASCII 塞进 `architecture_diagram.diagram`，type 仍写 `mermaid` → render.py 不校验 diagram 内容，HTML 里 mermaid 解析失败，**前端报错但脚本退出码 0**，用户看到坏图。
- 自己把 ASCII 翻译成 mermaid → 翻译质量参差。

**改法**（P0）：render.py 加一道**轻量 mermaid 启发式校验**：diagram 字符串首行必须匹配 `^(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie|journey)`，否则报 schema 错。这能强迫 agent 真翻译或省略 architecture 段。SKILL.md 步骤 3 加"如果 plan 里只有 ASCII 图，**把它翻译成 mermaid flowchart**；翻译有困难就把 `architecture_diagram` 字段整个删掉，让该 section 不出现"。

---

## 6. error path / 容错

`SchemaError` 信息形如 `字段 X 必须是 str, got NoneType`。agent 自我修复友好性：

- **优点**：错误明确指出字段路径（`decisions[3].status`）和期望类型。LLM 能直接定位重写。
- **缺点 1**（P2）：当 agent 漏掉 `meta.title` 时，错误是"`meta.title` 必须是 str, got NoneType"——agent 可能误以为是 type 问题，去填 `None` 或空字符串。**改法**：把"缺失字段"和"类型错"区分成两种错误："字段 `meta.title` 缺失" vs "字段 X 类型错"。
- **缺点 2**（P1）：agent 改一处错误后重跑，可能立刻撞到下一处。**没有"一次性返回所有 schema 错误"**——agent 会陷入修一处跑一次的循环，浪费 token。**改法**：`validate()` 收集所有错误后一并抛出，错误信息列表式：

  ```
  schema 校验失败 (3 处):
    - meta.title 缺失
    - decisions[2].status 必须是 chosen|rejected|deferred, got 'accepted'
    - risks[0].mitigated 必须是 bool, got 'yes'
  ```

- **死循环风险**：当前 schema 错误信息中文 + 英文混杂（"字段 X 必须是 Y, got Z"）。如果 agent 误以为要把 `got Z` 也当字段值，可能填错。**改法**（P2）：错误信息改为纯一种结构，比如 JSON：`{"errors": [{"path": "decisions[2].status", "actual": "accepted", "expected": "chosen|rejected|deferred"}]}` 输出到 stderr。LLM 解析结构化错误比解析自然语句稳。

---

## 7. 如果只能改 3 处

按 P0/P1 影响力综合：

1. **SKILL.md 步骤 1 加入"用 commit 关键词交叉验证 plan 文件"**（§1.1）—— 8 个 plan 时 agent 选错的概率太高，错一开始全错。
2. **render.py `validate()` 加"数量下限 + mermaid 启发式 + 全错误聚合"三重收紧**（§3.6、§5.3、§6 缺点 2）—— 这是把 SKILL.md 的"软约束"硬化进脚本的关键，agent 才不会跳过质量要求。
3. **JSON schema 把 `meta.git_range: str` 升级成 `meta.commits: list[str]` + `git_range` 兜底**（§3.3、§5.2）—— 当前字段在分支已合并 / fork 出 sub-feature 等真实场景下会塌；改成 commit list 后 agent 显式列举，读者一目了然，且原生兼容场景 (b)。

---

## 附：未在前面展开的小项（P2，备录）

- `meta.subtitle` 在示例里用了，模板没提到。模板加一行"可选副标题"。
- `out_of_scope[]` 是 list[str]，与 plan 模板的 bullet 一一对应，没问题；但缺失"为什么不做"维度，可考虑升级成 list[{item: str, why_not?: str}] —— 不急。
- `decisions[].cost` 是 optional string，但模板里建议每条都写。schema 不强制是对的（避免 agent 编造），保持现状。
- README 没在评估范围里，但 §4 的 plan-template-gap 1（Architecture summary）若被采纳，README 用法部分也要同步。
