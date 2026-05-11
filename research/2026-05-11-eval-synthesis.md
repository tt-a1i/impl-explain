# impl-explain 评估综合 · 优化行动清单

**日期**: 2026-05-11
**输入**: 4 份并行 Opus 评估
- `2026-05-11-eval-design.md` — 视觉设计 critique
- `2026-05-11-eval-information.md` — 信息架构 / reader UX
- `2026-05-11-eval-skill.md` — SKILL.md 可执行性 + JSON schema
- `2026-05-11-eval-cross-agent.md` — 三家实际部署可行性

---

## 核心结论（10 秒读完）

当前版本**视觉风格已达"好看"基线**，但有 4 类系统性短板：

1. **视觉断点** — 白色 mermaid 卡片是唯一 dashboard 残留；唯一冷色 chosen 绿与暖色调打架
2. **reader 30 秒可读性弱** — Risk 埋第 6 屏；决策卡片标题是问句；5500px 无导航
3. **schema 软约束没被硬化** — agent 容易跳过"≥3 决策"等质量要求；status=rejected 语义混乱；git_range 单字符串在分支已 merge 时塌
4. **跨 agent 真实部署有翻车点** — Codex 沙箱拒 `find ~`；4 份副本无 staleness check；项目根没定义；opencode 壳子绕开原生工具

---

## P0 行动清单（必改，按修改文件分组）

### A. `scripts/render.py` — 改 CSS / JS / 渲染逻辑

| # | 改动 | 来源 |
| --- | --- | --- |
| A1 | `--bg-card: #fdfaf3`（卡片改奶油色，消除白色 dashboard 断点）+ JS `themeVariables.background: '#fdfaf3'` 同步 | 视觉 P0 |
| A2 | `--chosen: #4a6a2c` / `--chosen-soft: #ecefd9`（冷绿改橄榄，全暖色相环） | 视觉 P0 |
| A3 | 决策序号 `.decision .num`: `font-size: 56px; color: var(--rule)`，列宽 `60px → 88px`，gap `24 → 32px` | 视觉 P0 |
| A4 | `validate()` 加：`len(decisions) ≥ 1`、`len(risks) ≥ 1`（强制最低门槛，含 SKILL.md 引导文本提示） | schema P0 |
| A5 | `validate()` 加：mermaid 启发式校验——`architecture_diagram.diagram` / `data_flow.before/after` 首行必须匹配 `^(flowchart\|graph\|sequenceDiagram\|...)`，否则 ASCII art 塞进去会让 HTML 静默坏掉 | schema P0 |
| A6 | `validate()` 改为**一次性收集所有错误后聚合返回**（避免 agent 修一处跑一次的循环） | schema P0 |
| A7 | 删 `decisions[].status="rejected"`，剩 `chosen` / `deferred` 二态（rejected 语义跟 chosen 字段冲突） | schema P0 |
| A8 | schema 加 `meta.commits: list[str]` 字段；`meta.git_range` 降级为可选 fallback（分支已 merge 后 `main..HEAD` 返回空，commits list 是更稳的语义） | schema P0 |
| A9 | TL;DR 下方加 **Risk Snapshot 段**（"5 risks · 1 high mitigated · 2 unmitigated medium"一行汇总） | IA P0 |
| A10 | 决策卡片重构：标题改**结论式短句**（不带问号），字段顺序调成 `chosen → rationale → rejected → cost`；`status=deferred` 整体降饱和（如 opacity 0.85 + 序号灰） | IA P0 |
| A11 | 顶部加 **sticky TOC**（7 段横排 + 当前位置高亮）+ 1px 高的滚动 progress bar | IA P0 |
| A12 | Before/After 段位置上移，紧贴 Architecture（同属"结构变化"语义） | IA P0 |

### B. `SKILL.md` — 改指令

| # | 改动 | 来源 |
| --- | --- | --- |
| B1 | 步骤 1 加 "用 commit 关键词交叉验证 plan 文件"——先 `git log <base>..HEAD --format=%s%n%b` 收集本次实施关键词，与 `docs/superpowers/plans/*.md` 文件名/标题做重合度排序，差距 <2 个关键词时**问用户**而非猜（多 plan 仓库选错概率太高） | schema P0 |
| B2 | 步骤 2 加场景兜底：`git log <base>..HEAD` 返回空时，fallback `git log -10 --no-merges` + 让用户确认；输出 `commits: list[str]` 字段（配合 A8） | schema P0 |
| B3 | 步骤 5 显式加 `git rev-parse --show-toplevel` 计算项目根；失败退回 CWD 并在步骤 6 报告里说明实际写入位置 | 跨家 P0 |
| B4 | 步骤 5 兜底路径列表**加 `~/.agents/skills/impl-explain/scripts/render.py`**（调研推荐的 primary 安装位，原列表漏了） | 跨家 P0 |
| B5 | 步骤 5 **删除 `find ~ -path '*/impl-explain/scripts/render.py'` 兜底**——Codex 沙箱常拒，4 条显式路径已够 | 跨家 P0 |
| B6 | description 第一句加限定词"在用户**已经完成一次 implementation 工作后**…"，收窄触发时机，避免 Claude Code auto-invoke 过早 | 跨家 P0 |
| B7 | "字段质量要求"段：删除 `status="rejected"` 选项，保留 `chosen` / `deferred` 二态 | schema P0 |

### C. `install.sh` / `README.md` / 壳子 — 改部署/兼容性

| # | 改动 | 来源 |
| --- | --- | --- |
| C1 | `install.sh` 增加 `--status` 子命令——对 4 份目标与 `SOURCE_DIR` 做文件 hash 比对，发现漂移就 warn | 跨家 P0 |
| C2 | `install.sh` 装 `~/.codex/prompts/impl-explain.md` 时打印 "Codex prompts 已被官方标 deprecated，未来需迁移到 /skills 菜单" warn | 跨家 P0 |
| C3 | `README.md` 安装段加 **staleness 警告**："copy 模式下修改源仓库后必须重跑 `./install.sh --force`，否则 4 份副本不会自动更新" | 跨家 P0 |
| C4 | `README.md` 兼容性矩阵：Codex slash 那行改成 "✓（fallback，未来需迁移）"；opencode 那行注明 "依赖 agent 自觉读 SKILL.md，无 slash 原生支持" | 跨家 P0 |
| C5 | `slash-wrappers/opencode-command.md` 改成两段式 fallback：**先**指示 agent 尝试 `skill({name: 'impl-explain'})` 原生工具，**失败**再 read 文件路径 | 跨家 P0 |
| C6 | `slash-wrappers/codex-prompt.md` 顶部加注释 "本壳子是 fallback，custom prompts 已 deprecated，未来用 `/skills` 菜单或 mention 触发" | 跨家 P0 |

---

## P1 行动清单（强烈建议）

### 视觉

| # | 改动 |
| --- | --- |
| P1-V1 | `flow-cell` padding `24/20 → 32/24` + grid gap `20 → 28`（与 diagram-wrap 一致节奏） |
| P1-V2 | `--rejected: #7a2f24` / `--rejected-soft: #f1ddd5`（避免和 terracotta accent hue 撞色） |
| P1-V3 | LOW severity 颜色单独定 `#a89970` 而非复用 text-muted |
| P1-V4 | letter-spacing 收成三档：0.12 / 0.16 / 0.22 em，按场景固定（详见 design 报告 §2） |
| P1-V5 | mermaid `themeVariables.fontSize: '14px'` + `flowchart.padding: 12` + `lineColor: '#a89685'`（更暖） |
| P1-V6 | Decisions 之间 gap `56 → 72px` + 每条决策末尾加发丝分隔（`::after`） |
| P1-V7 | Rejected line 字体从 Fraunces italic 改 Inter upright，让 italic 唯一保留给 cost |
| P1-V8 | section `margin: 96 → 80px`，hero meta padding-top `24 → 32px` |
| P1-V9 | Before/After 标签色对仗：before terracotta、after olive |

### 信息架构

| # | 改动 |
| --- | --- |
| P1-IA1 | TL;DR 字段命名 `目标 / 方案 / 权衡` → `做什么 / 怎么做 / 代价`（更口语，30 秒读者友好） |
| P1-IA2 | Hero 加 3 个 metric chip：决策数 / 风险数（high 数）/ sources unified |
| P1-IA3 | TL;DR.tradeoff vs Decision.cost 规则：TL;DR 写整体账（架构总账、运维总账），Decision 写局部账（单点选 A vs B 的代价） |
| P1-IA4 | Architecture 下方加 italic caption 说明颜色编码（"橙色块 = 新增；箭头标签 = dispatch kind"） |
| P1-IA5 | Risks 段顶部加汇总行：`Total 5 · High 1 (mitigated) · Medium 2 · Low 2` |
| P1-IA6 | Out of Scope 砍到 3-4 条核心边界，去重 Decisions 已隐含的点 |

### Schema / SKILL

| # | 改动 |
| --- | --- |
| P1-S1 | `risks[].mitigated: bool` 升级为 `mitigation: "full" \| "partial" \| "none"` 三态（真实风险常常是 partial） |
| P1-S2 | description 把触发短语前移、压缩 "用于 X、Y、Z" 句式（Codex `/skills` 菜单截断阈值最严） |
| P1-S3 | SKILL.md 输入数据来源优先级段：plan 没 `## Decisions` 时**先 grep commit body** 找 why/because/考虑过；还是不够 3 条就**停下来问用户**，不要 silently 从代码瞎猜 |
| P1-S4 | `architecture_diagram` 新增 `summary: str?` 字段（容纳 plan 模板里 mermaid 上方那 2-3 句叙述） |
| P1-S5 | plan-template.md 加一行说明 "agent 提取 risks 时把 `— severity` 之前的部分作为 description"（避免行内 metadata 被当 description 带进去） |

### 跨家

| # | 改动 |
| --- | --- |
| P1-X1 | description 在 SKILL.md 文件顶部加 HTML 注释 "description 上限 1000 char（Codex `/skills` 菜单匹配阈值最严）"，给未来编辑者锚点 |

---

## P2 行动清单（可选 / 收尾）

- 删 `architecture_diagram.caption` 字段（agent 99% 不填，模板没提）—— 或者扩到 plan-template.md 触发
- Hero subtitle 字号 `22 → 26px`（与 TL;DR body 拉开层级）
- `.cost::before` "代价 — " 改成"代价" + 发丝竖线分隔（与全文 hairline 风格一致）
- Out of Scope `×` 改 em-dash（去掉 todo app 残留）
- Eyebrow `.dot` 与 footer `.end-mark` 尺寸统一成 6×6（首尾呼应）
- `validate()` 错误信息：区分"字段缺失"和"类型错"两种错误模式；改成 JSON 结构输出（LLM 解析更稳）
- `decisions[].rejected` 升级为 `list[str] \| list[{name, why_not}]`（保留现状也行）

---

## 推荐执行批次

**Batch 1（视觉收敛，30 分钟）**: A1 + A2 + A3 + P1-V1~V9。一次改 `scripts/render.py` 顶部 CSS 和 JS 常量，立刻见效。

**Batch 2（信息架构重排，1-2 小时）**: A9 + A10 + A11 + A12 + P1-IA1~IA6。需要改 `render_*` 函数 + 加新 section 渲染 + sticky TOC JS。改后视觉效果质变。

**Batch 3（schema 硬化 + SKILL 鲁棒性，1 小时）**: A4-A8 + B1-B7 + P1-S1~S5。集中改 `validate()` + SKILL.md + plan-template.md。一气呵成。

**Batch 4（跨家鲁棒性，30 分钟）**: C1-C6 + P1-X1。文件分散但都是小改动。

**Batch 5（P2 收尾，按心情）**: 视觉细节微调，影响小但精致度++。

---

## 信息源

- `/Users/admin/code/impl-explain/research/2026-05-11-eval-design.md`
- `/Users/admin/code/impl-explain/research/2026-05-11-eval-information.md`
- `/Users/admin/code/impl-explain/research/2026-05-11-eval-skill.md`
- `/Users/admin/code/impl-explain/research/2026-05-11-eval-cross-agent.md`
