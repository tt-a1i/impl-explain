# impl-explain

> 给 AI agent 用的 skill：把刚做完的 implementation plan + git 变更，渲染成一份**单文件 HTML 实施报告**。
> 适合开会前 30 秒对齐团队、向 reviewer 解释设计决策、归档实施叙事。

跨 agent 通用，**Claude Code / Codex CLI / opencode** 三家都能用。

---

## 这份报告长什么样

每份 HTML 报告包含以下结构（没有的段会优雅跳过）：

| 段 | 内容 |
| --- | --- |
| **Hero** | 大号衬线标题 + 副标题 + 3 个 metric chip（决策数 / 风险数 / 自定义）+ plan path / commits |
| **顶部 sticky TOC** | 5 段锚点导航，当前位置 terracotta 高亮，伴随滚动 progress bar |
| **TL;DR** | 三行：做什么 / 怎么做 / 代价（整体账，不复述决策局部 cost）|
| **Risk Snapshot** | 紧跟 TL;DR 的风险概览：总数 + severity 分布 pill + 缓解比例 |
| **Architecture** | mermaid 流程图，可选 summary 在图上方、caption 在图下方，新组件用强调色高亮 |
| **Before / After** | 数据流改动前后并排对比（mermaid） |
| **Decisions** | 编号决策卡片：结论式短标题 + 可选原问题副标题 + 采用 / 理由 / 放弃 / 代价 |
| **Risks** | 风险清单，按 severity 染色，标 mitigation 三态（full / partial / none） |
| **Out of Scope** | 故意没做的事，italic 列表 |

视觉风格：浅色编辑风（warm cream 背景 + Fraunces 衬线大标题 + Inter 正文 + JetBrains Mono 标签），不是 dashboard。

样例输出：`examples/unified-source-sync-manager.html`（直接双击在浏览器打开）。

## 设计哲学

**HTML 是叙事，不是 changelog。**

读者已经能 `git diff` 看代码改动，但看不到：

- 你为什么选 A 不选 B
- 哪些事故意没做
- 哪些事可能出问题

这份 skill 强制 agent 在生成 HTML 时把这三类信息抽出来，**用结构化字段表达**。如果信息薄弱，不允许靠加节点 / 加文件清单 / 加 commit list 充数——`validate()` 会卡 `decisions ≥ 1`、`risks ≥ 1`、mermaid 语法等硬约束。

文件地图段刻意没有——reviewer 想看哪些文件改了，自己 `git diff --name-status` 一行命令。

## 安装

### 一键安装（推荐）

```bash
git clone https://github.com/<TODO>/impl-explain.git
cd impl-explain
./install.sh
```

安装后会把 skill 放到三家 agent 都能读到的位置，并装 Codex / opencode 的 slash 触发壳子。Claude Code 自动暴露 `/impl-explain`，无需额外配置。

> ⚠️ **Copy 模式 staleness 警告**：默认 copy 模式下，4 份副本独立存在。**修改源仓库后必须重跑 `./install.sh --force`**，否则 4 份副本不会自动更新。用 `./install.sh --status` 随时检查漂移。

### 开发模式（symlink）

边改 skill 边迭代用 symlink 模式，目标位置直接指向源仓库，源改了立即生效：

```bash
./install.sh --link
```

### 其他选项

```bash
./install.sh --force        # 覆盖已存在的安装（修改源后必跑）
./install.sh --no-wrappers  # 只装 skill, 不装 Codex/opencode 壳子
./install.sh --status       # 检查 4 份副本是否与源同步
./install.sh --uninstall    # 移除所有安装位置
./install.sh --help
```

## 用法

实施工作做完后（plan 写好、代码 commit、想生成对齐文档时），在 agent 会话里：

| Agent | 触发方式 | 备注 |
| --- | --- | --- |
| **Claude Code** | 输入 `/impl-explain` | 原生 slash，零配置 |
| **Codex CLI** | 输入 `/impl-explain`（prompts 壳子，**fallback**），或 `/skills` 菜单选 | Custom prompts 已被官方标 deprecated；未来用 `/skills` 菜单 |
| **opencode** | 输入 `/impl-explain`（commands 壳子，先尝试原生 `skill()` 工具） | 无原生 slash，依赖 commands 壳子转发 |

可选参数：plan 文件路径。比如 `/impl-explain docs/superpowers/plans/2026-05-11-foo.md`。

agent 会自动：

1. 找到 plan 文件（多 plan 仓库时用 commit 关键词交叉验证，必要时问用户）
2. 跑 `git log` + `git diff --name-status` 收集 commits
3. 综合成 JSON
4. 调用本 skill 的 `render.py` 生成 HTML
5. 把 HTML 路径告诉你

HTML 输出到 **`git rev-parse --show-toplevel`** 计算出的项目根 `impl-explain.html`（如果不在 git repo 中，落到 CWD 并显式告知），**默认不 commit**——是否提交由你自己决定。

## 怎么写 plan 让 agent 输出质量更高

agent 综合 JSON 时依赖以下信息源（按优先级）：

1. plan markdown 里的显式段落（`## Decisions`、`## Risks`、`## Out of Scope`、`## TL;DR`）
2. 对话历史里你和 agent 讨论过的决策
3. commit message body 里的 "why" / "because" / "考虑过" 关键词
4. 实际代码（最后兜底）

**最简单提升报告质量的方式**：写 plan 时用配套模板 `templates/plan-template.md`，把决策 / 备选 / 风险 / out-of-scope / metrics 显式记录下来。agent 不需要靠推断填字段，结果稳定且高质量。

## JSON Schema（agent 内部用）

完整 schema 详见 `scripts/render.py` 顶部 `validate()` 函数。简版：

```json
{
  "meta": {
    "title", "subtitle?", "date", "plan_file",
    "commits?": ["sha subject"],
    "git_range?": "main..HEAD (fallback)",
    "metrics?": [{"label", "value", "hint?"}]
  },
  "tldr": {"goal", "approach", "tradeoff"},
  "architecture_diagram": {"type": "mermaid", "diagram", "summary?", "caption?"},
  "data_flow": {"before", "after"},
  "decisions": [
    {"title", "question?", "chosen", "rejected[]", "rationale", "cost?", "status"}
  ],
  "risks": [
    {"description", "severity", "mitigation", "note?"}
  ],
  "out_of_scope": [string]
}
```

枚举 / 硬约束：

- `decisions[].status` ∈ `chosen` / `deferred`（`rejected` 已废弃；属于 `out_of_scope`）
- `risks[].severity` ∈ `low` / `medium` / `high`
- `risks[].mitigation` ∈ `full` / `partial` / `none`（兼容旧字段 `mitigated: bool`）
- `decisions[]` 必须 ≥ 1 条
- `risks[]` 必须 ≥ 1 条
- mermaid 字符串必须以 `flowchart`/`graph`/`sequenceDiagram` 等关键字开头，否则 schema 拒绝（防止 ASCII art 让 HTML 静默坏掉）

## 自定义视觉

改 `scripts/render.py` 顶部的 `CSS` 和 `JS` 常量。配色 token 在 CSS `:root` 里，统一改色调一处即可。Mermaid 主题在 `JS` 的 `themeVariables`。

字段加减：调 `validate()` 和对应 `render_*()` 函数，记得同步 `SKILL.md` 的 JSON schema 文档。

## 已知限制 / 兼容性矩阵

| 项 | Claude Code | Codex CLI | opencode |
| --- | --- | --- | --- |
| skill 自动发现 | ✓ | ✓ | ✓ |
| `/impl-explain` slash 直接触发 | ✓（原生） | ✓（prompts 壳子，**fallback**——未来需迁移到 `/skills` 菜单） | ✓（commands 壳子，先尝试原生 `skill()` 工具，失败再读文件） |
| description 字符上限 | 1536 | ~1000 | 1024 |
| 默认沙箱 `find ~` 兜底 | ✓ | ✗（已禁用，依赖 4 条显式路径） | ✓ |

description 控制在 1000 字符内，三家都安全。

**Mermaid CDN 需要联网**——离线场景目前不支持，未来用 inline `mermaid.min.js` 解决。

**单进程渲染**——跨 plan 浏览 / 索引不在当前版本范围内（roadmap 见下）。

## Roadmap

- v1（当前）：单文件 HTML，每次跑都重新生成，不持久化索引
- v2 候选：plan 模板 lint（检查必填段是否齐全）
- v3 候选：本地 React 站点，跨 plan 浏览，跨 PR 链接
- v4 候选：HTML 内嵌 mermaid（无 CDN，可离线）

## 项目结构

```
impl-explain/
├── README.md                   # 这份
├── SKILL.md                    # 主 skill 文件（跨 agent）
├── install.sh                  # 一键安装 + --status / --uninstall / --link
├── scripts/
│   └── render.py               # JSON → HTML 渲染器（Python stdlib only）
├── templates/
│   └── plan-template.md        # 配套 plan 模板，让 agent 综合 JSON 更准
├── slash-wrappers/
│   ├── codex-prompt.md         # → ~/.codex/prompts/impl-explain.md (deprecated fallback)
│   └── opencode-command.md     # → ~/.config/opencode/commands/impl-explain.md (两段式 fallback)
├── examples/
│   ├── unified-source-sync-manager.input.json   # demo 输入
│   └── unified-source-sync-manager.html         # demo 产出
├── docs/plan/                  # 本项目自身的 implementation plan
├── research/                   # 三家 skill 格式调研 + 4 份评估报告
└── 2026-05-11-brainstorm.md    # 起因 + 思路收敛记录
```

## License

MIT
