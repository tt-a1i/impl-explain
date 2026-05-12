# v2 lite SKILL.md 可执行性评估

**评估方式**：扮演被 `/impl-explain` 触发的 agent，站在 `/Users/admin/work/de/global-hotspot-globe` 仓库下走完 SKILL.md 4 步，记录心理日志。

---

## A. 模拟执行 SKILL.md 4 步

### 步骤 1：找 plan（心理日志）

读到 SKILL.md 第 27 行"多 plan 仓库交叉验证"，第一反应**很犹豫**。这个仓库的 `docs/superpowers/plans/` 里有 **187 个 plan**（不是 18，是 187），按日期最新选明显不靠谱——同一天经常 3 个 plan。

跑算法：

- `git log main..HEAD` 显示 **200+ commits**（远超 30 阈值，SKILL.md 说要压缩成 first..last，但 token 收集时显然得用完整 set）
- 提取 commit token：`pulse`, `source`, `gdelt`, `rss`, `taxonomy`, `adapter`, `sync`, `audit`, `agent`, `geo`, `relation`, `frontend`, `content`, `geocoding`, `entity`...
- top 候选 plan：`2026-05-11-unified-source-sync-manager.md`, `2026-05-11-gdelt-gkg-ingester.md`, `2026-05-11-taxonomy-backend-alignment.md`, `2026-05-12-live-data-layers-foundation.md`, `2026-05-09-new-pulse-source-review.md`

心算 overlap：unified-source-sync 跟 commit token 集会命中 `source`/`sync`/`pulse`/`gdelt`/`rss`（≈ 8-10）；gdelt-gkg-ingester 命中 `gdelt`/`audit`/`ingester`（≈ 5-7）；taxonomy 命中 `taxonomy`/`backend`/`align`（≈ 6-8）。**top1 - top2 大概率 ≤ 3**，算法会 bounce 到"问用户"。**这其实是对的**——但 SKILL.md 没说清"问用户怎么问"，agent 会自己编一个 UX：列 top 3 让用户选？还是只问 yes/no？建议加一行 fallback 话术模板。

更硬的问题：SKILL.md 让我取 plan 的"特征段落 = 文件名去日期 + h1 + `## TL;DR` + `## Decisions` 的 `###` 子标题"。我 grep 了一下：**187 个 plan 里只有 1 个有 `## Decisions` 段**（包括当前 git status 列出的 `2026-05-09-new-pulse-source-review.md` 自己都没有）。这仓库的 plan 风格是 `## Goal` + `## Tasks`，**不是** impl-explain 模板风格。算法 token set 直接退化成"文件名 + h1"——区分度大幅下降，top1-top2 ≥ 3 这个阈值几乎总会触发"问用户"。**算法没坏，但 fallback 路径才是常态而不是 corner case**，SKILL.md 应该把"问用户"写成 first-class 步骤，而不是当兜底。

停用词列表（`superpowers/tracking/plan/implementation`）够窄，没纳入 `backend`/`frontend`/`feat`/`add`/`fix`/`feat(content)` 这种本仓库 commit 前缀里出现几十次的 token——会把"加东西"型 plan 都拉到中等 overlap。

### 步骤 2：收集 commits（心理日志）

`git symbolic-ref refs/remotes/origin/HEAD --short` 在当前 branch `codex/agent-normalizer-poc` 上能拿到 `origin/main`，OK。

但 `git log main..HEAD` 出来 **200+ 行**——这个仓库 main 落后非常多。SKILL.md 说 > 30 压缩成 `first..last (N commits)` 一行。**这条规则在这里反而有害**：当前 branch 跨了 N 个不相关 feature 的 commits（agent normalizer / geo aggregation / RSS batch-1~20 / pulse adapters / relation network…），压缩成一行等于丢失"哪几条属本次 plan"的信息。

SKILL.md 在"空 commits"分支提到"让用户确认哪几条属本次"，**但在"超 30 条"分支没这条**——这是不对称。建议：> 30 时**也**让用户确认范围（或者用 plan 日期作为隐式 cut-off）。当前规则会让 agent 把 200 条压成 `5f1c7b8 .. f05f467 (217 commits)`，HTML 里 Hero 那条 commits chip 直接失去意义。

### 步骤 3：写 HTML（心理日志，这是最大的怀疑点）

读到第 47 行"直接读它、抄它的 CSS / 字体 / mermaid 配色 / 整体布局"——我会**犹豫一下到底要不要把 sample.html 全读完**。sample.html 是 **1073 行**，CSS 块从第 8 行延伸到 ~700 行，纯 vibes 提示让我倾向"扫前 200 行抓 token 然后自己写 CSS"。SKILL.md **没有一句"读完整 sample.html"或"必须 verbatim 复制 CSS/JS 块"** 的强约束。第 122 行说"完整 CSS / JS 直接从 sample.html 复制"——更像 reminder 而不是 must。

**这是 v2 lite 最脆弱的点**。v1 有渲染管线兜底 CSS，v2 lite 完全依赖 agent 把 1073 行参考 verbatim 复制。在上下文压力下我大概率会复制前 1/3，然后"按相同风格"自己写后 2/3——结果就是字体引用对、配色对、但 `.risk-row` `.decision .num` `.tldr-risk-tail` 这些细节类名 / margin / 间距全飘移。**跨报告一致性会以肉眼可见的速度退化**。

**mermaid 安全 shim 同样脆**。SKILL.md 第 128-132 行用散文描述了规则（`htmlLabels: false` + `data-content` attribute + JS 复制回 textContent），但**没贴具体 JS 代码**。我得自己去 sample.html 第 976-983 行找。要是我没翻那么深，会自作聪明用"安全的"`innerHTML = JSON.stringify(...)`——XSS regress 静默发生，HTML 看着没坏。这是真正的 P0。

7 段"必填 vs 可选"——TL;DR 第 67 行说"做什么/怎么做/代价"三行，但**没说"如果 plan 里 TL;DR 段不存在"怎么办**。这仓库大部分 plan 没 TL;DR 段（参考 `2026-05-09-new-pulse-source-review.md` 第一段是 `## Goal`），我得自己合成或跳过整段。Architecture / Decisions / Risks 同理。

mermaid `classDef newcomp` 颜色：SKILL.md 给了完整 directive `fill:#fbeede,stroke:#b04a1f,...`，可复制——**这一条 OK**。

mitigation 三态同义词列表：**partial 列里包含"已沉淀"** 让我犹豫——sample.html 里"已沉淀"出现在 `partial` note 里，但前提是后接"future 接 Prometheus"。"已沉淀"单独出现明显是 `full`（落地了）。这条同义词触发条件太宽，建议改为"已沉淀 + future/后续"组合才匹配 partial。小问题。

### 步骤 4：报告路径（心理日志）

`git rev-parse --show-toplevel` → `/Users/admin/work/de/global-hotspot-globe/impl-explain.html`，清晰可执行。**但**：固定文件名 `impl-explain.html`，二次跑（不同 plan）会**静默覆盖**前一次的 HTML，没 timestamp 也没 plan slug。不致命但坑。

---

## B. v1 vs v2 关键能力对比

| 失守项 | v2 还能阻止吗 |
| --- | --- |
| 0 decision / 0 risk 水报告 | **不能强卡**。SKILL.md 第 86/99 行只有"建议 3-8 条"和"至少 1 条"的散文。Agent 读完 plan 没找到 decisions 段时会跳过整段（这是 SKILL.md 第 59 行明确允许的）。**而本仓库 99.5% 的 plan 没显式 Decisions 段**——agent 大概率给出一份没有 Decisions section 的报告。这跟"叙事密度 > 信息覆盖度"的设计取向**部分一致**（信息不够就不凑），但偏离了 impl-explain 的核心价值主张（"为什么这么做"卡片）。 |
| ASCII 图塞进 mermaid 段 | **不能**。v1 用正则 `^(flowchart\|graph\|sequenceDiagram\|...)\b` 卡过。v2 完全靠 LLM 自觉。但因为 sample.html 全是 mermaid，actor agent 多半会 follow——风险中。 |
| LLM 自创视觉风格 | **半阻止**。sample.html 是强 anchor，但前面说过 1073 行硬复制在上下文压力下不稳。视觉一致性会退化 ~15-30%（margin / 字号 / 类名漂移），不会完全失控。 |

---

## C. 三个最可能失败的场景

- **(a) plan 没 `## Decisions` 段**：**本仓库的常态**（186/187 命中）。v2 兜底 = 跳过整段。报告里没 Decisions = impl-explain 价值丢失大半。SKILL.md 应在步骤 3 加一句"如果 plan 缺核心段落，先回过头问用户能不能补一段简短的 decisions 叙事，而不是直接跳过"。
- **(b) 仓库不在 git**：SKILL.md 第 45 行说"不在 git repo 时落 CWD 并显式告诉用户位置"——**可执行**。但步骤 2 整段假设 git 存在，没说"不在 git 时跳过整个 commits 收集"。会卡死。
- **(c) plan 是纯叙述 markdown**：v2 没解析器，agent 通读全文做总结——这个其实**比 v1 更宽容**，是 v2 lite 的合理收益。OK。

---

## D. SHIP / NEED FIX

**判定：NEED FIX（2 条 P0/P1，不凑数）**

1. **【P0】mermaid 安全 shim 必须在 SKILL.md 里贴具体 JS 代码片段**，不能只靠散文描述 + "去 sample.html 找"。XSS regress 是静默的，agent 漏读 sample.html 第 976-983 行就会发生。代价：SKILL.md 多 8 行代码块。
2. **【P1】"完整 CSS / JS 直接从 sample.html 复制"必须升级为强约束**——比如开头加一句"**第一步：把 sample.html 完整读进上下文，CSS/JS 块整段 verbatim 复制，不要自己重写**"。同时把当前 plan 仓库的实际形态（大量 plan 没 `## TL;DR` / `## Decisions`）写进步骤 3 的"plan 段落缺失"分支，明确指引"问用户能不能补一段叙事，而不是默默跳过"。

其余（多 plan 算法阈值偏严但已 fallback 到问用户、固定文件名覆盖、partial 同义词"已沉淀"歧义、> 30 commits 压缩与 plan 范围冲突、停用词表不全）都是 P2 细节，可以 ship 后迭代。

**结论：NEED FIX**（修上面两条，约 30 分钟工作量，之后可 ship）。
