---
name: impl-explain
description: 在用户已经完成一次 implementation 工作后，把项目里的 implementation plan + git diff/log 渲染成一份单文件 HTML 实施报告。报告包含 TL;DR、风险概览、架构图（mermaid）、Before/After 数据流、决策记录卡片、风险清单。用于开会前快速对齐团队、向 reviewer 解释设计决策、归档实施叙事。当用户说"生成实施报告"、"impl-explain"、"explain implementation"、"展示这次实施方案"、"做一份 HTML 实施总结"时调用本 skill。
---

<!-- description 上限 1000 char（Codex /skills 菜单匹配阈值最严，三家中最低）。修改时务必保留触发关键词在前 200 char。 -->

# impl-explain

## 用途

把一次刚做完的实施任务整理成单文件 HTML 报告。**代码细节不在范围内**（reviewer 想看 diff 自己 `git diff`），重点是**为什么这么做、考虑过什么、放弃了什么、留了什么坑**——这些信息只存在于实施当时，错过就丢了。

## 触发时机

仅在用户已经**完成一次实施**且希望生成可视化总结时调用。常见请求：

- "生成实施报告" / "做一份 impl-explain" / "把这次实施画成 HTML"
- "show me what this PR did" / "explain the implementation in HTML"

如果用户只是闲聊 "explain the implementation"、或者实施还没做完、或者还没 commit 任何东西，**不要 auto-invoke**——询问用户是否要现在生成报告。

## 执行步骤

下面六步**按顺序**做，不要跳步。任何一步出错，停下来询问用户而不是猜测。

### 步骤 1：定位 plan 文件

**默认查找路径**（按优先级）：

1. 用户在请求里指定了 plan 路径——用那个
2. `docs/superpowers/plans/` 下日期最新的 `.md`
3. `docs/plans/` 下日期最新的 `.md`
4. 项目根目录下符合 `*plan*.md` 模式的最新文件

**多 plan 仓库的交叉验证（重要）**：如果第 2/3 类目录下有 **超过 1 个 plan 文件**，"日期最新"不够准——它不一定是本次实施对应的那个。必须做交叉验证：

**算法（显式化避免 agent 间发散）**：

1. **commit token set**：跑 `git log <base>..HEAD --format='%s%n%b'`，把所有 commit subject + body 拼成字符串，按非字母数字（包括 `-` `_` `.`）分隔成 token；**过滤掉**：
   - 停用词（the / a / and / for / with / 的 / 了 / 和 / 一个 / 这个 / 改 / 加 / 修 / 让）
   - 长度 ≤ 2 的 token
   - 纯数字 token
   - **plan 模板里的 boilerplate**（如 `superpowers` / `tracking` / `required` / `plan` / `executing` / `implementation` / `agentic` / `workers` / `checkbox` / `syntax`——这些每个 plan 都有，会造成假命中）
   小写化后去重得到 `commit_tokens`
2. **每个 plan 的 plan token set**：**只取 plan 的"特征段落"**，**不要整篇**（整篇有大量模板 boilerplate 会污染）。具体取：
   - **文件名**（去掉前缀日期 `YYYY-MM-DD-` 和后缀 `.md`）
   - **第一个 `#` 标题（h1）**
   - **`## TL;DR` 段落或 `## Goal` 段落**的全文
   - **`## Decisions` 段落里所有 `### Decision` 子标题**的文本

   按同样规则切 token + 同样的停用词 + boilerplate 过滤，得 `plan_tokens`
3. **重合度（命中数）**：`overlap = |commit_tokens ∩ plan_tokens|`
4. **排序 + 决策**：按 overlap 倒序取 top1 / top2。**如果 top1.overlap - top2.overlap ≥ 3**（注意：阈值从 2 提到 3，因为 boilerplate 过滤后剩余 token 噪声降低，但仓库大时 false positive 仍可能），选 top1；否则**停下来问用户**："仓库里有多个 plan 候选（top1 / top2，重合度 X vs Y），本次实施对应哪一个？"

**额外安全网**：即使 top1-top2 差距 ≥ 3，如果 top1 的 overlap < 5（说明所有 plan 都低相关），**也停下来问用户**。

不要靠模糊匹配 / 余弦相似度——LLM 间发散；token set 命中数是确定性的。

如果都找不到 plan，告诉用户："未找到 plan 文件。请指定路径，或先写一份 plan 再跑 impl-explain。" 然后**停止**。

读取该 plan 的完整内容备用。

### 步骤 2：收集 git 上下文

获取本次实施的代码变更范围。需要的信息：

1. **base 分支**：先 `git symbolic-ref refs/remotes/origin/HEAD --short` 拿默认分支（通常 `origin/main` 或 `origin/master`）；失败则 fallback `main` → `master`
2. **commit 列表**：`git log <base>..HEAD --format='%h %s' --no-merges`
   - 如果输出为空（说明本分支已合并 / fast-forward），改用 `git log -10 --no-merges` 取最近 10 条，**让用户确认哪几条属于本次实施**
   - 如果超过 30 条，可压缩成 `"<short SHA1> .. <short SHAN> (N commits)"` 单字符串
3. **改动文件清单**：`git diff <base>..HEAD --name-status`（只用来辅助你理解实施范围，**不要嵌进 HTML**）

JSON 里输出的是 `meta.commits: list[str]`，每条形如 `"abc1234 commit subject"`。HTML 是叙事不是 changelog，文件级 diff 不展示。

**如果 commits 超过 30 条**：长 commit 列表会把 hero 区撑得太长。建议：(a) 用一行压缩 `"<short_first> .. <short_last> (N commits)"` 当唯一 commits 项；(b) 或问用户 "本次 PR 改动很大（N commits），要不要拆成多份报告？"

### 步骤 3：综合输入 JSON

根据 plan 内容 + git 上下文 + 你和用户的对话历史，组装一份 JSON。**严格按下面的 schema**，字段名和类型不能错，否则渲染会失败：

```json
{
  "meta": {
    "title": "<本次实施的核心标题, 一行>",
    "subtitle": "<可选, 一句话副标题, 出现在标题下>",
    "date": "<YYYY-MM-DD>",
    "plan_file": "<plan 的相对路径>",
    "commits": ["<short SHA + subject>", "..."],
    "git_range": "<可选 fallback, 比如 main..HEAD>",
    "metrics": [
      {"label": "<短中文/英文>", "value": "<大数字或值>", "hint": "<可选小字>"}
    ]
  },
  "tldr": {
    "goal": "<一句话目标, ≤60 字。说做什么>",
    "approach": "<一句话采用方案, ≤80 字。说怎么做>",
    "tradeoff": "<一句话整体账, ≤60 字。说总代价>"
  },
  "architecture_diagram": {
    "type": "mermaid",
    "summary": "<可选, 图上方的 2-3 句叙述>",
    "diagram": "<mermaid 源码, 必须以 flowchart/graph/sequenceDiagram 等开头>",
    "caption": "<可选, 图下方的 italic 说明>"
  },
  "data_flow": {
    "before": "<改动前的数据流 mermaid 源码>",
    "after": "<改动后的数据流 mermaid 源码>"
  },
  "decisions": [
    {
      "title": "<结论式短标题, 比如 '集中注册表放 cadence'>",
      "chosen": "<最终选择, 一两句话>",
      "rejected": ["<拒绝的备选 1>", "<拒绝的备选 2>"],
      "rationale": "<选择的理由, 2-4 句>",
      "cost": "<可选, 本条决策的局部代价>",
      "status": "chosen"
    }
  ],
  "risks": [
    {
      "description": "<风险描述, 不要把 plan 行内的 '— severity: X' metadata 当成描述带进来>",
      "severity": "high",
      "mitigation": "full",
      "note": "<可选, 缓解措施 / 观察方法 / 触发条件>"
    }
  ],
  "out_of_scope": [
    "<故意没做的事, 具体一句话>"
  ]
}
```

**字段取值（严格）**：

- `decisions[].status`: 仅 `chosen` 或 `deferred` 二选一。**`rejected` 已废弃** —— 如果一个决策的所有备选都被否决，那它应该出现在 `out_of_scope` 里，而不是 decisions。
- `decisions[].title` 必填（结论式短句，**渲染时作为决策卡的唯一标题**）。
- `decisions[].question` **已废弃，不要再填**。schema 仍然接受（兼容旧 JSON），但**不再渲染**——IA 评估认定与 title 冗余。直接把结论写到 title 即可。
- `risks[].severity`: `low` / `medium` / `high`
- `risks[].mitigation`: `full` / `partial` / `none`。**rule of thumb**（同义词列表，命中任一视为 partial 或 none）：
  - `partial`：note 含 "future" / "后续" / "后期" / "长期" / "上线后" / "上线后再调" / "TODO" / "暂未" / "未接入" / "已沉淀" / "已记录" / "部分覆盖" / "long-term" / "down the road" / "需补"
  - `none`：note 含 "未做" / "尚未观测" / "未来加" / "计划中" / "暂时不做" / "待+动词"（如"待评估"、"待补充"、"待 leader election"）/ "needs to be done" / "not yet"
  - `full`：note 描述了**已经生效**的具体阻断机制（如"启动时 strict 校验"、"测试覆盖"、"flag 判断保证不会同时挂载"）
  - 不确定时倾向写 `partial`，比 `full` 更诚实

**字段质量硬约束**（validator 会卡）：

- `decisions[]`：必须 ≥ 1 条；推荐 3-8 条。挑那些"反过来选会出大问题"的关键决策。
- `risks[]`：必须 ≥ 1 条；推荐 2-5 条。**"无风险" 是不真实的**——至少想想"多副本部署"、"依赖第三方"、"静默失败"这三类。
- `architecture_diagram.diagram` / `data_flow.before/after`：**必须**以 mermaid 关键字开头（flowchart / graph / sequenceDiagram / classDiagram / stateDiagram 等）。ASCII art 塞进去会被 validator 拒绝。如果 plan 里只有 ASCII，**把它翻译成 mermaid**；翻译困难就**省略这个字段**让该 section 不出现。

**字段质量软约束**（自查）：

- **TL;DR 三句必须 30 秒讲完**。不要堆 CamelCase / 不要复述 plan 标题。
- **TL;DR.tradeoff 写整体账，不写局部账**。"换走 X 复杂度，引入 Y 风险" 这种宏观陈述，**不要**复述任何一条 Decision 的 cost。
- **决策的 `title` 是结论式短句**，不是带问号的提问。把"做了什么决定"放在 title，原问题留给可选的 `question` 字段做副标题。
- **架构图至少 5 个节点**。展示新组件与既有系统的关系。新组件高亮用 `classDef newcomp fill:#fbeede,stroke:#b04a1f,color:#1f1c17,stroke-width:1.5px` + `class A,B,C newcomp`——**不要**写 `style X fill:#暗色` 这种暗黑色值，会跟浅色主题打架。
- **out_of_scope 要具体**。"未来可能优化" 太空泛；写 "暂未做 leader election" 这种具体项。
- **`metrics` 没填的话，render.py 会自动派生**（决策数 + 风险数）。如果你想显式定义（如 "源类型收敛 4→1"），就填进去。

### 步骤 4：把 JSON 写到临时文件

把上一步的 JSON 写到一个临时文件。优先 `/tmp/impl-explain-input.json`；如果 `/tmp` 不可写（Codex 严格沙箱场景）回落到项目根 + `.impl-explain.input.json`（**记得提示用户加进 .gitignore**）。

### 步骤 5：调用 render.py 生成 HTML

调用本 skill 目录下的渲染脚本。命令模式：

```
python3 <SKILL_DIR>/scripts/render.py --input <JSON 路径> --output <PROJECT_ROOT>/impl-explain.html
```

**关于 `<PROJECT_ROOT>`**：用 `git rev-parse --show-toplevel` 显式计算项目根。如果不在 git repo 中（命令失败），退回当前 CWD，**并在步骤 6 报告里显式告诉用户 HTML 实际写到了哪个目录**。

**关于 `<SKILL_DIR>`**：本 SKILL.md 所在的目录就是 SKILL_DIR。**按以下优先级查找 render.py**：

**P1 · 读 manifest 文件**（install.sh 安装时写入；最稳）：

```
cat ~/.config/impl-explain/manifest.json   # 输出 {"skill_dir": "<绝对路径>"}
```

如果 manifest 存在且 `skill_dir/scripts/render.py` 也存在，直接用，跳过下面所有步骤。

**P2 · SKILL.md 所在目录**：多数 agent framework（Claude Code / Codex 加载 skill 时）会把 SKILL.md 的绝对路径放进 agent 上下文。agent 用 `dirname` 拿到当前 SKILL.md 所在路径 + `/scripts/render.py`。

**P3 · 显式路径列表**（按顺序查找，**第一个存在的即用**）：

```
~/.agents/skills/impl-explain/scripts/render.py
~/.claude/skills/impl-explain/scripts/render.py
~/.codex/.agents/skills/impl-explain/scripts/render.py
~/.config/opencode/skills/impl-explain/scripts/render.py
```

**P4 · 有限范围 fallback**：如果上面都没命中，做**受限的 find**（**不是** `find ~`，限定在 agent 配置目录内，避免 Codex 沙箱拒绝 + 全盘扫描噪声）：

```
find ~/.claude ~/.codex ~/.config ~/.agents -maxdepth 6 -type f -path '*impl-explain*' -name 'render.py' 2>/dev/null
```

如果仍然找不到：直接告诉用户 "impl-explain skill 未安装。请先 `git clone <repo>` 并运行 `./install.sh`，会自动写入 `~/.config/impl-explain/manifest.json` 让 skill 跨仓库可达。"，然后**停止**。不要尝试 `find ~` 或更大范围——慢、噪声、沙箱拒绝。

**成功标志**：脚本退出码 0，stdout 输出 "✓ 报告已生成: <绝对路径>"。

**失败处理**：如果脚本报多行 "schema 校验失败:"——**所有错误会一次性列出**，按错误信息修正 JSON 的对应字段，重新跑步骤 4-5。不会出现修一处跑一次的循环。

### 步骤 6：报告路径给用户

告诉用户：

- HTML 文件的**绝对路径**（如果是 fallback CWD 写入而非 git root，**显式说明**）
- 简短统计：N 个决策卡片、N 条风险（含 N 个 high）
- "双击 HTML 即可在浏览器查看，无需启动 server"

## 不要做的事

- **不要**把 git diff 的具体行嵌入 HTML（违反"叙事不是 changelog"原则）
- **不要**给 HTML 改样式 / 加新 section / 减少 section（要改就改 render.py，不要在调用时 hack）
- **不要**在 plan 信息不够时编造决策。如果 plan 没记载某个权衡：**先 grep commit body** 找 "why" / "because" / "因为" / "考虑过" 关键词；如果还是不够 3 条，**停下来问用户** "plan 里没记录决策，要不要口头补几条？"——不要 silently 从代码瞎猜
- **不要**把 schema 中没有的字段塞进 JSON，validator 会拒绝
- **不要**把 HTML 输出到 git 仓库的源码目录里造成噪声。默认输出到项目根目录下的 `impl-explain.html`，是否 commit 由用户自己决定

## 输入数据来源优先级

当 plan 文件里没有结构化字段（比如没有显式 `## Decisions` 段）时，按以下优先级填充 JSON：

1. plan markdown 里的显式段落（`## Decisions`、`## Risks`、`## Out of Scope`、`## TL;DR`）
2. 对话历史里用户和你讨论过的决策
3. commit message body 里的 "why" / "because" / "考虑过" 关键词
4. 实际代码（最后才看；如果只能靠代码推断，在对应字段里标 "(从代码推断)"）

**plan 缺 `## Decisions` 段的兜底流程**：

1. 先 grep commit body → 多数情况能补出 2-3 条决策
2. 仍然不够 3 条 → **停下来问用户**："plan 里没记录决策，要不要口头补几条？" 不要直接从代码瞎猜决策

## 设计哲学

这份 skill 输出的 HTML **不是文档**，**不是 changelog**，**是叙事**。

读者不在乎你改了多少行代码（自己 `git diff` 看得到），但在乎：

- 你为什么这么干而不是那么干
- 哪些事故意没做
- 哪些事可能出问题

如果 JSON 里这三类信息薄弱，不要靠加节点 / 加 commit list / 加 file 清单充数。**叙事密度 > 信息覆盖度**。
