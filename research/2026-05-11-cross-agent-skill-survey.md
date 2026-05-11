# 跨 agent skill 可移植性调研（Claude Code / Codex / opencode）

日期：2026-05-11
目标读者：主代理（在 `/Users/admin/code/impl-explain` 实现 `impl-explain` skill 之前先看这份）

## 1. 三家 skill 文件格式

| 维度 | Claude Code | OpenAI Codex CLI | opencode |
|---|---|---|---|
| 存放位置（user） | `~/.claude/skills/<name>/SKILL.md` | `$CODEX_HOME/.agents/skills/<name>/SKILL.md`（即 `~/.codex/.agents/...`），同时也扫描 `$HOME/.agents/skills`、`/etc/codex/skills` | `~/.config/opencode/skills/<name>/SKILL.md`，**也读** `~/.claude/skills` 和 `~/.agents/skills` |
| 存放位置（project） | `.claude/skills/<name>/SKILL.md` | `$REPO_ROOT/.agents/skills/<name>/SKILL.md`，外加 `$CWD/.agents/skills` 与父目录 | `.opencode/skills`、`.claude/skills`、`.agents/skills`（都识别） |
| 文件名 | `SKILL.md`（目录名即 skill 名） | `SKILL.md` | `SKILL.md` |
| frontmatter 必填 | `description` 建议；`name` 可省（取目录名） | `name`、`description` | `name`（正则 `^[a-z0-9]+(-[a-z0-9]+)*$`，1–64 char）、`description`（1–1024 char） |
| frontmatter 可选 | `name` / `when_to_use` / `argument-hint` / `arguments` / `allowed-tools` / `disable-model-invocation` / `user-invocable` / `model` / `effort` / `context: fork` / `agent` / `hooks` / `paths` / `shell` | `allowed-tools`（在 `agents/openai.yaml` 旁文件里声明），`policy.allow_implicit_invocation` | `license` / `compatibility` / `metadata`（key-value map）；**unknown 字段被忽略**——这点对可移植性是利好 |
| body 语法 | Markdown + 特殊语法：`` !`cmd` `` 注入 shell 输出、` ```! ` 多行 shell、`$ARGUMENTS` / `$0..$N` / `$name` / `${CLAUDE_SKILL_DIR}` 等 | Markdown，无 shell 注入；旧版 prompts 支持 `$1..$9` / `$ARGUMENTS` / `$NAMED`，新版 skills 文档**未明确**这套占位符是否依然适用 | Markdown；占位符 / shell 注入未在 skill 文档中列出（命令文档里 opencode 命令支持 `$ARGUMENTS`、`!`cmd``、`@file`） |
| 发现/加载 | 启动时扫描上述目录 + 监听文件变更；嵌套 `.claude/skills/` 也自动识别 | 启动时扫描；`~/.codex/config.toml` 可禁用 | 启动时扫描；on-demand 通过 `skill` 工具加载 body |
| 触发 | `/<skill-name>`（slash） + 自动按 description 匹配；`disable-model-invocation: true` 关闭自动 | `/skills` 菜单、`$skillname` mention、自动匹配 description；**没找到** `/<skill-name>` 直接斜杠触发的明确支持（CLI 用 `/skills` 进入选择菜单） | agent 通过 `skill` 原生工具 `skill({name})` 调起；**无 slash 入口** |
| 子目录支撑文件 | `scripts/`、`references/`、任意 | `scripts/`、`references/`、`assets/`、`agents/openai.yaml` | 文档未列出明确子目录约定，但 SKILL.md 同目录的文件 skill 自己可以引用 |
| skill 调 skill | Claude Code 通过 Skill 工具可以调，本质是同一个 Skill 工具的另一次调用 | **未找到** 明文支持 | **未找到** 明文支持（但 agent 可以连续 `skill()` 调） |

## 2. Slash command 体系

- **Claude Code**：custom commands 已合并进 skills。`.claude/commands/<name>.md` 与 `.claude/skills/<name>/SKILL.md` 都生成 `/<name>`，行为一致。skill ≡ slash command。
- **Codex**：custom prompts 在 `~/.codex/prompts/*.md`，文件名变成 slash 名（`my-prompt.md` → `/my-prompt`）；frontmatter 支持 `description` / `argument-hint`。但官方文档已**把 custom prompts 标记为 deprecated**，推荐改用 skills。slash 触发 skill 走 `/skills` 菜单或 `$name` mention，不像 Claude Code 那样有原生 `/<skill-name>`。
- **opencode**：custom commands 与 skills 是**两个独立机制**。命令在 `~/.config/opencode/commands/*.md` 或 `.opencode/commands/*.md`，文件名即 slash 名；skills 单独存在，靠 agent 主动调 `skill` 工具，**没有 slash 入口**。

结论：**没有一种"同一文件同时是 skill + slash command"在三家全部生效**。最接近通用的方式是写两份等价产物：一份 SKILL.md（被自动发现 / agent 工具调用），一份命令薄壳（在 Claude Code 和 opencode 都注册 slash；Codex 走 `~/.codex/prompts/`）。

## 3. 工具能力的共同子集

| 能力 | Claude Code | Codex | opencode | 评估 |
|---|---|---|---|---|
| 读文件 | Read | apply_patch / shell `cat` | read | 全部支持 |
| 写文件 | Write / Edit | apply_patch | write / edit | 全部支持 |
| 跑 shell | Bash | shell | bash | 全部支持，名字不同 |
| glob / list dir | Glob / LS | shell `ls`/`find` | glob / list | 全部支持 |
| 网络抓取 | WebFetch（受限） | 默认沙箱内**不允许** | 可配置 | 本项目不需要 |
| Web search | WebSearch | 视模式而定 | 可配置 | 本项目不需要 |

工具命名差异是真实存在的（`Read` vs `read` vs apply_patch 风格）。**skill 指令应避免点名工具**，用动词叙事（"读取 plan 文件"、"列出 git log"）即可，让各家自己映射到本地工具。

## 4. HTML 产出方式可移植性

- (a) **agent 直接写 HTML 字符串** — 三家都能做（都有 Write 类工具）。但 LLM 直接吐长 HTML 字符串容易截断、格式漂移、token 浪费。
- (b) **skill 内含 Python 脚本，agent 调用脚本生成 HTML** — Claude Code 官方示例就是这种（`${CLAUDE_SKILL_DIR}/scripts/visualize.py`）；Codex skills 文档明确支持 `scripts/` 子目录；opencode 没有明确说脚本子目录约定，但 agent 能跑 bash 调任何脚本。

**推荐 (b)**。但 `${CLAUDE_SKILL_DIR}` 这种宏只 Claude Code 有，Codex / opencode **未找到** 等价路径变量。最稳：让脚本通过 stdin 读 JSON 数据 + 写到 `$CWD/impl-explain.html`，并在 SKILL.md 中要求 agent **先 `cd` 到 skill 目录**或用 `find` 拼出脚本绝对路径。

## 5. 推荐的最小公约数方案

### 5.1 skill 文件

```yaml
---
name: impl-explain
description: 读取 plan markdown + git diff/log, 生成单文件 HTML 实施报告. 用于实施完成后向团队展示决策/架构图/风险.
---
```

只用 `name` + `description`。其余字段（`allowed-tools`、`when_to_use`、`paths` 等）三家行为不一致，**全部省略**。

body 用纯叙事 markdown，不点名工具：

```markdown
## 输入
1. 在 docs/superpowers/plans/ 下找最新 plan markdown.
2. 读取该 plan 的内容.
3. 运行 git log 拿最近的相关 commit, 运行 git diff 拿当前差异.

## 处理
... (步骤化指令)

## 输出
调用本 skill 目录下 scripts/render.py, 将上述数据写入当前目录的 impl-explain.html.
```

### 5.2 三家安装路径

发布 skill 包时同一份 SKILL.md 复制 / symlink 到下列路径之一：

| Agent | 推荐安装位置 |
|---|---|
| Claude Code | `~/.claude/skills/impl-explain/SKILL.md` |
| Codex | `~/.codex/.agents/skills/impl-explain/SKILL.md` |
| opencode | `~/.config/opencode/skills/impl-explain/SKILL.md` 或直接复用 `~/.claude/skills`（opencode 也读）|

实际上 opencode 同时扫 `~/.claude/skills`、Codex 也扫 `~/.agents/skills`。**最省事**：把 skill 装到 `~/.agents/skills/impl-explain/`（Codex 扫；opencode 扫）+ `~/.claude/skills/impl-explain/`（Claude Code 扫；opencode 也扫）两处 symlink。

### 5.3 slash 入口

- Claude Code：自动得到 `/impl-explain`，零额外工作。
- Codex：用户 `/skills` 菜单选；如要 slash 直触发，多放一份壳子到 `~/.codex/prompts/impl-explain.md`，内容只是"调用 impl-explain skill"（虽然 deprecated，但当前仍可用）。
- opencode：多放一份命令壳到 `~/.config/opencode/commands/impl-explain.md`，内容里告诉 agent 调用 skill。

### 5.4 是否做 conditional 分支

**不做**。指令文本完全用人类语言（"读文件"、"跑 git log"），不点名 Read/Bash/shell。三家的 agent 自己知道怎么映射。这是开源 Agent Skills 标准（agentskills.io，Claude Code 文档明确遵循）的核心动机。

## 6. 已知风险 / 不兼容点

1. **slash 触发不统一**。Claude Code 有 `/<skill-name>`，Codex 走 `/skills` 菜单或 `$mention`，opencode 完全没 slash 入口，必须由 agent 主动调 `skill` 工具或写个 command 壳子。**最大风险点**。
2. **frontmatter 字段不兼容**。Claude Code 那些好用的 `disable-model-invocation`、`allowed-tools`、`paths`、`context: fork` 在 Codex / opencode 里被忽略或未定义。好消息是 opencode 明文"unknown 字段被忽略"；Codex / Claude Code 也容忍。但**不能依赖** Claude Code 专有字段的行为。
3. **shell 注入语法 (`` !`cmd` ``) 只有 Claude Code 支持**。Codex / opencode 的 skill body 里这是普通 markdown 文本。所以 dynamic context injection 不能写进通用 skill；要在 body 里写"指令"让 agent 自己跑 shell。
4. **`${CLAUDE_SKILL_DIR}` / `$ARGUMENTS` 这类占位符是 Claude Code 私有**。Codex skills 文档没确认 `$ARGUMENTS` 在 skill 内还有效（只在旧 prompts 里讲）；opencode skills 文档干脆没提占位符。**通用 skill 不要依赖占位符**。
5. **Codex custom prompts 已被官方标 deprecated**。如果走"额外写一份 `~/.codex/prompts/impl-explain.md` 作为 slash 入口"的策略，要在 README 说明这是 fallback，未来 Codex 可能下线。
6. **脚本路径**。Claude Code 有 `${CLAUDE_SKILL_DIR}`，Codex / opencode **未找到** 同等变量。脚本要么用相对 `./scripts/render.py` 并依赖 agent `cd` 到 skill 目录，要么 skill 指令告诉 agent 自己 `find ~/.claude/skills ~/.codex ~/.config -name render.py`，不漂亮但能跑。
7. **Codex `/skills` 命令对 description 截断阈值更严**（约 2% context / 8000 字符），description 写得太冗长会被切。Claude Code 上限 1536 字符，opencode 1024 字符。**统一上限按 1000 字符以内写 description**，关键场景放最前面。
8. **opencode 没有 slash 直触发 skill**，依赖 agent 自动选。如果 agent 不主动调，用户只能间接说"用 impl-explain 的方式生成报告"。

## 建议的下一步行动

1. 先在 `~/.claude/skills/impl-explain/` 起骨架，用 Claude Code 跑通端到端（最快反馈环），但**克制使用** Claude Code 专有 frontmatter / 占位符。
2. 写 `scripts/render.py`，输入 stdin JSON / 命令行参数，输出 HTML 到 `$CWD/impl-explain.html`；不用 `${CLAUDE_SKILL_DIR}`，让 SKILL.md 在指令里用人话说"运行本 skill 目录下的 scripts/render.py"。
3. 在仓库 README 写明三家的安装路径（symlink 命令一行搞定），以及 Codex / opencode 用户的 slash 触发壳子（可选）。
4. 用 Codex / opencode 本地各跑一遍 smoke test，确认两家 agent 在 description 触发下能正确读 plan + 跑 git + 调脚本。如果 Codex 总是触发不到，调整 description 的关键词。
5. 把 description 控制在 1000 字符内，关键触发词（"implementation plan"、"git diff"、"HTML report"）放前 200 字符。

## 信息源

- [Claude Code Skills 官方文档](https://code.claude.com/docs/en/skills)
- [Claude Code Slash Commands](https://code.claude.com/docs/en/slash-commands)
- [opencode Skills 官方文档](https://opencode.ai/docs/skills/)
- [opencode Commands 官方文档](https://opencode.ai/docs/commands/)
- [Codex Agent Skills](https://developers.openai.com/codex/skills)
- [Codex Custom Prompts](https://developers.openai.com/codex/custom-prompts)
- [Codex Slash Commands (built-in)](https://developers.openai.com/codex/cli/slash-commands)
- [Agent Skills 开放标准 agentskills.io](https://agentskills.io)
