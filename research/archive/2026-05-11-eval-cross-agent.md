# impl-explain 跨 agent 部署可行性评估

日期：2026-05-11
评估对象：`/Users/admin/code/impl-explain/` 当前快照
目标：模拟 Claude Code / Codex CLI / opencode 三家 agent 真实运行此 skill，识别每家具体翻车点并给修补建议。

---

## 共性问题（先于三家 section）

### C1（P0）`<项目根>` 没定义

`SKILL.md` 步骤 5 第 123 行让 agent 把 HTML 写到 `<项目根>/impl-explain.html`，但全文从未说"项目根"怎么计算。三家 agent 的 CWD 语义不一样：Claude Code 跟用户当前 shell，Codex 通常是 repo root，opencode 是 session 起始目录。结果是 agent 各自猜——有时 HTML 落到 `~/`，有时落到 `docs/`，有时落到 `scripts/`。

**修补**：在 `SKILL.md` 步骤 5 显式加一条指令——"用 `git rev-parse --show-toplevel` 计算项目根；若该命令失败（不在 git repo 中），退回到当前 CWD，并在步骤 6 报告里告诉用户实际写入位置"。

### C2（P0）4 份安装副本无 source-of-truth

`install.sh` 默认 copy 模式把 SKILL.md + render.py 复制到 4 个目录（`~/.agents/skills/`、`~/.claude/skills/`、`~/.codex/.agents/skills/`、`~/.config/opencode/skills/`）。用户改了仓库里的 `SOURCE_DIR/SKILL.md` 之后，4 份副本静默过期，下次跑 skill 仍然读旧版。`install.sh` 没有 `--status` / 没有 hash check / 没有 staleness 提示，`README.md` 第 42 行也没警告 copy 模式的这一陷阱。

**修补**：(a) `install.sh` 加 `--status` 子命令，对 4 份目标和 SOURCE 做 hash 比对，发现漂移就 warn；(b) `README.md` 在"安装"段加一句"修改源仓库后必须重跑 `./install.sh --force`，否则 4 份副本不会自动更新"；(c) 把 `--link` 提升为默认或在 `./install.sh` 没参数时给一句"推荐 dev 用 --link"的提示。

### C3（P1）`find` fallback 在沙箱里不可靠

`SKILL.md` 步骤 5 第 135 行兜底用 `find ~ -path '*/impl-explain/scripts/render.py' 2>/dev/null`。问题：(a) Codex 默认 read-only / workspace-write 沙箱可能拒绝读取 `$HOME` 范围之外；(b) 即使允许，`find ~` 在大 home 目录下慢、噪声大；(c) opencode 的 bash 工具默认权限随用户配置变。前面 4 条显式路径已经覆盖三家所有标准安装位置，`find` 兜底带来的代价大于价值。

**修补**：删掉 `find ~` 兜底，改成"如果 4 条显式路径都没命中，告诉用户 skill 未安装、提示运行 `install.sh`，然后停止"。

### C4（P2）python3 调用方式

`SKILL.md` 步骤 5 用 `python3 <SKILL_DIR>/scripts/render.py`，render.py 自身 shebang 是 `#!/usr/bin/env python3`。三家在标准 macOS / Linux 上都能解析。devcontainer / Codespaces 里偶有 `python` 但无 `python3` 的奇葩情况，但 `install.sh` 第 131 行已经在安装时 check 过，运行时再失败的概率小。不优化也行。

---

## Claude Code

### 实际运行链路
触发 `/impl-explain` → Claude Code 直接读 `~/.claude/skills/impl-explain/SKILL.md` → 按步骤跑 Bash/Read/Write → 调用 `python3 .../scripts/render.py`。

### 最可能失败的步骤

**F1（P2）双入口冲突——经核实不存在**：任务描述担心 `.claude/skills/impl-explain/SKILL.md` 与 `.claude/commands/impl-explain.md` 同时存在会冲突。核查 `install.sh` 第 29-35 行，脚本**没有**安装到 `.claude/commands/`，因此冲突不存在。仅当用户手动放过同名 command 时才需要担心，文档可加一句"如果你自己在 `.claude/commands/` 放过同名文件，请删除以避免歧义"。

**F2（P1）`/skills` 自动匹配可能过早触发**：description 含"explain implementation"、"生成实施报告" 等高频短语；用户即便只是闲聊"explain the implementation"也可能被 auto-invoke。`SKILL.md` 没有 `disable-model-invocation` 字段（survey 也建议不要用 Claude 专有字段）。
**修补**：description 第一句加一个限定词，比如"在用户**已经完成**一次 implementation 后……"——把 trigger 时机收窄。

**F3（P2）输出落点**：见 C1。Claude Code 多数时候 CWD 是用户当前 shell，行为最稳定，但仍建议 `git rev-parse` 显式化。

### onboarding 风险点
第一次 `/impl-explain` 自动加载，体验最顺。最大风险是用户在没 plan 文件的目录直接触发，SKILL.md 步骤 1 第 35 行规定了停机问询的行为，没问题——前提是 agent 严格遵守，不要"贴心地"自动写一份 plan。

---

## Codex CLI

### 实际运行链路
两条入口竞争：(a) `~/.codex/prompts/impl-explain.md`（custom prompt 壳子，已被官方标 deprecated）— slash 直接触发；(b) `~/.codex/.agents/skills/impl-explain/SKILL.md`（skill 自动发现，走 `/skills` 菜单或 `$impl-explain` mention）。

### 最可能失败的步骤

**F4（P0）双入口优先级未定义**：用户输 `/impl-explain`，Codex 命中 prompt 壳子；用户走 `/skills` 菜单，命中 skill 本体；用户在对话里写 `$impl-explain`，命中 mention 匹配。三条路最终都跳转去执行 SKILL.md 步骤 1-6，行为应当一致——但 `codex-prompt.md` 第 8-12 行的路径顺序是 codex → primary → claude，没强调"找到第一个就停"，agent 可能加载多次 SKILL.md。更严重的是，custom prompts 已 deprecated，未来 Codex 下线该机制后 `/impl-explain` 直接失效。
**修补**：(a) `codex-prompt.md` 顶部加注释"本壳子是 fallback，未来用 `/skills` 菜单或 mention 触发"；(b) `README.md` 兼容性矩阵那行（第 142 行）把 Codex 的 ✓ 改为 ✓（fallback，未来需迁移）；(c) `install.sh` 在装这份壳子时打印一行 warn 提示用户。

**F5（P1）description 截断**：survey §6.7 提到 Codex 对 description 截断阈值约 8000 字符，但 `/skills` 选择菜单里实际展示长度更短。当前 description 332 字符，关键词"生成实施报告"、"impl-explain"、"explain implementation"前置，安全。但如果未来扩展，要守住 1000 字符上限。
**修补**：在 `SKILL.md` 文件顶部加 HTML 注释"description 上限 1000 char（Codex `/skills` 菜单匹配阈值最严）"，给未来编辑者锚点。

**F6（P0）沙箱 + `find ~` 翻车**：Codex 默认 read-only / workspace-write 沙箱模式下，`find ~ -path ...` 极可能被拒。即便用 `--full-access`，跨 `$HOME` 扫描在企业 CI 里也常被审计拦。当前 `SKILL.md` 第 135 行的 `find` 兜底在 Codex 最容易坏。
**修补**：同 C3，删 `find` 兜底，依靠 4 条显式路径 + 显式 install 提示。

### onboarding 风险点
Codex 用户**第一次**触发时，三条入口（slash / `/skills` 菜单 / mention）描述不一致会让人懵：他们打 `/impl-explain`，得到的是 prompt 壳子加载的 SKILL.md 体验，但官方文档已经把 prompts 标 deprecated——新用户搜文档时会找不到对应说明。`README.md` 必须有一段"Codex 用户特别说明"，写清当前 prompts 壳子是过渡方案。

---

## opencode

### 实际运行链路
opencode 原生不支持 slash 触发 skill；当前 `~/.config/opencode/commands/impl-explain.md` 壳子要 agent **加载 SKILL.md 文件**（而不是调用 opencode 的 `skill` 工具）。

### 最可能失败的步骤

**F7（P0）壳子绕开了 opencode 原生 `skill` 工具**：`opencode-command.md` 第 7-13 行直接列出 SKILL.md 路径让 agent 去 read，没有先尝试 `skill({name: "impl-explain"})`。这意味着 opencode 自带的 skill 发现/加载机制（包括 lazy body 加载、模型 invocation policy）被完全跳过，等价于把 skill 当普通 markdown 文件来用。如果未来 opencode 给 skill 加 sandboxing / permission gating，本壳子直接绕过，反而是个隐患。
**修补**：`opencode-command.md` 改成两段——先指示 "尝试调用 `skill({name: 'impl-explain'})` 原生工具"，失败或不可用时再 fall back 到读文件路径。

**F8（P1）agent 是否真的跑 `find` / bash**：survey §3 表格里 opencode 的 bash 工具是有的，但 agent 在默认配置下不一定主动用 bash 跑 find——它更倾向用 `read` / `list` 工具循环试 4 条路径。这其实更好。前提是 SKILL.md 步骤 5 不把 `find` 写得像唯一选项。
**修补**：见 C3，删掉 `find` 兜底，反而让 opencode agent 更稳。

**F9（P2）CWD 与项目根**：opencode session CWD 通常是用户启动 session 时所在目录，不一定是 repo root。`SKILL.md` 步骤 5 的"项目根"歧义在 opencode 最尖锐。
**修补**：同 C1。

### onboarding 风险点
opencode 用户第一次输 `/impl-explain` 走到 command 壳子，agent 按指令读 SKILL.md——但**没人保证 agent 会主动调用 `skill()` 工具**。如果未来 opencode 调整 commands 行为或加权限闸门，今天写的壳子可能直接失效。建议在 `README.md` opencode 那一栏（第 142 行）注明"依赖 agent 自觉读 SKILL.md，无 slash 原生支持"。

---

## 翻车概率 × 修复成本 优先级总表

| 编号 | 项 | 翻车概率 | 修复成本 | 优先级 |
|---|---|---|---|---|
| C1 | `<项目根>` 未定义 | 高（三家都中） | 低（SKILL.md 加 2 行） | P0 |
| C2 | 4 份副本无 source-of-truth | 中（用户改源后） | 中（install.sh 加 --status + README 一段） | P0 |
| F4 | Codex 双入口 + prompts deprecation | 中（短期；长期=高） | 低（README + install.sh 加 warn） | P0 |
| F6 | Codex 沙箱内 `find ~` 失败 | 高（默认沙箱即翻） | 极低（删 SKILL.md 一行） | P0 |
| F7 | opencode 壳子绕开原生 skill 工具 | 中（短期；长期=高） | 低（opencode-command.md 改两段） | P0 |
| C3 | `find` fallback 不可靠 | 中 | 极低 | P1 |
| F2 | Claude Code auto-invoke 过早 | 中 | 低（description 加限定词） | P1 |
| F5 | Codex description 截断未来风险 | 低 | 极低（加注释锚点） | P1 |
| F8 | opencode agent 不跑 bash | 低 | 0（被 C3 顺手解决） | P1 |
| F1 | Claude Code 双入口冲突 | 0（不存在） | 0 | P2 |
| C4 | python3 调用方式 | 极低 | 0 | P2 |
| F3 / F9 | 三家 CWD 差异 | 被 C1 覆盖 | — | P2 |

---

## 如果只能修 3 处，修哪 3 处

1. **`SKILL.md` 步骤 5**——加一句"用 `git rev-parse --show-toplevel` 显式计算项目根，失败则退到 CWD 并在步骤 6 报告里说明"，同时**删掉** `find ~ -path '*/impl-explain/scripts/render.py'` 兜底。一次改动同时解决 C1、C3、F6，对三家都是直接收益，特别是救活 Codex 沙箱场景。

2. **`install.sh` + `README.md` 加 staleness 警告**——`install.sh` 增加 `--status` 子命令（对 4 份目标与 SOURCE 做文件 hash 比对，发现不一致就警告）；`README.md` 在"安装"段加一句"copy 模式下修改源仓库后必须 `./install.sh --force`"。解决 C2，防止用户改完源代码以为生效、实际跑的是旧版的硬伤。

3. **`opencode-command.md` 改两段式**——先让 agent 尝试 `skill({name: "impl-explain"})` 原生工具，失败再读文件路径；同时在 `codex-prompt.md` 顶部加一段"本壳子是 fallback，custom prompts 已 deprecated，未来用 `/skills` 菜单或 mention 触发"的注释。一次改动同时让 opencode 走官方路径（F7）+ 给 Codex 用户预警（F4），把两个"短期能跑、长期会塌"的隐患同步治掉。

三处加起来约 30 行编辑，没有架构动作，但把当前最大的"换个 agent 就翻"风险压到可控水位。
