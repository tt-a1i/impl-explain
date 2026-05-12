# v2 lite 整体简化合理性评估

**评估日期**：2026-05-12
**评估对象**：`impl-explain` 从 v1（JSON schema + render.py + 31 tests）重构为 v2 lite（纯 prompt skill）
**v1 基线**：tag `v1-structured-2026-05-11`（render.py 1487 行 / test_render.py 283 行 / SKILL.md 252 行）
**v2 现状**：SKILL.md 144 行 + sample.html 1073 行 + install.sh 162 行 + plan-template.md 175 行 + 双语 README

---

## A. 简化是否过头

### A1. 没了 `validate()` 硬卡，"至少 1 条" 文字提示有效力吗？— **是**

SKILL.md line 99 把硬卡换成"至少 1 条 + 三类常见隐患（多副本 / 第三方 / 静默失败）"的提示，line 93-97 还保留了 v1 攒下的 mitigation 同义词速查（partial 触发词 / none 触发词 / full 必须有阻断机制）。这套**思维支架**才是 v1 validate 的真正价值，不是"抛 ValueError"那一行代码。Prompt-only 把它从硬错误降级为软引导，对 Claude/Codex/opencode 这一档的 agent 来说**够了**——它们看到带数字下限的明确指令会照做。剩下的 5% 越界由 reviewer 兜底，可接受。

### A2. 没了 render.py 单一可信源，sample.html 当 visual anchor 够强吗？— **待观察**

sample.html 是**真 HTML、真 CSS、真 mermaid 初始化**（1073 行可执行物），不是描述。SKILL.md line 47 / line 108 / line 122 三次强调"读它、抄它，不要自创"。比"想象一份样式指南"强得多。但**风险**：当三个不同 session 各自"抄 sample.html"时，难免在 padding、hover、间距上微漂；v1 的 render.py 是单进程，零漂移。在团队规模 < 5 人 + 用同款 agent 时不会暴雷；规模上去后需要引入"diff 当前输出和 sample.html 的脚本"作为软检查。

### A3. 没了 unit test，HTML 出 bug 怎么发现？— **是（已可接受）**

v1 那 31 个 test 测的是 render.py 这个 Python 单元；v2 没有 Python 单元，自然也测不了。能测的只有"agent 生成的 HTML 是否符合预期"，但每次 agent 输出都不一样，单元测试无法稳定断言。**真正可行的替代**是 sample.html 本身——它就是 living regression baseline。这不是简化的代价，是架构变了所以测试对象变了。

### A4. v2 SKILL.md "安全约束" 段够让 agent 真做 mermaid 注入防御吗？— **是（关键设计）**

这是 v2 最容易翻车的点，但实际做对了：SKILL.md line 126-134 用**祈使句**列出 `htmlLabels: false` / `data-content` attribute / JS shim / 完整 HTML escape 四件套；**且 sample.html line 975-1007 真的实现了这套**——agent 被告知"抄 sample.html" 就**自动**带上防御。安全规范活在可执行参考里，比活在文档里强。这一步处理得比预期好。

### A5. 综合判断

A1-A4 单看都过线，A2 是唯一需要长期跟踪的——但触发条件需要团队 + 时间，PoC 阶段不阻塞 ship。

---

## B. 文档 / 安装路径 / 兼容性一致性

### B1. 残留的 v1 引用 — **`examples/sample.html:977`**

```
// 见 scripts/render.py::mermaid_text 注释。
```

`scripts/` 目录已删，这个注释指向不存在的文件。agent 读 sample.html 抄 JS 时会把这条注释也抄进新报告。**必须改**：删掉该行，或改为"完整 HTML escape mermaid 源 + JS shim 复制 data-content → textContent"的纯说明。

### B2. install.sh — **一致**

line 81-83 只 copy `SKILL.md` + `examples/sample.html`，没有任何 `scripts/` / `tests/` / `bin/` 残留路径。line 88-103 wrapper 安装路径准确指向 v2 的 slash-wrappers 目录。卸载逻辑（line 116-127）也只清理实际安装的资源。无问题。

### B3. README — **基本一致**

README.md line 43 / line 156、README.en.md line 44 / line 157 都明确写 "Prompt-only / no Python runtime"。line 47-48 提到 v1 仅作为历史脚注（`v1-structured-2026-05-11` tag + research/archive 链接），是**正确的归档式引用**而不是 v1 描述残留。Project structure 段（line 165-183）也对得上 v2 实际布局。无修改需求。

### B4. slash-wrappers — **一致**

codex-prompt.md 让 agent 按 SKILL.md "执行步骤" 4 步走（找 plan / 收集 git / 写 HTML / 报告路径），无 render.py 字样。opencode-command.md line 33 显式说"直接生成 HTML（不需要中间 JSON / 外部脚本）"——主动声明 v2 模式。

### B5. plan-template.md — **一致**

字段命名（TL;DR / Architecture / Data Flow / Decisions / Risks / Out of Scope）对应 SKILL.md 报告 section，无 JSON 字段残留。line 95 显式说 "status 只有 chosen / deferred，没有 rejected"——与 SKILL.md line 85 一致。

---

## C. 哪些保留物是冗余

### C1. `templates/plan-template.md` 175 行 — **保留，值钱**

不是"写不写都行"。SKILL.md 提取 plan 的能力受限于 plan 写法，模板的 4 个反例（Decision title 太短 / Risk 太宽泛 / Out of Scope 太空泛 / tradeoff 复述 Cost）每个都是 v1 evaluation report 里反复出现的踩坑。让用户先用模板写 plan，是最便宜的报告质量提升手段。**留**。

### C2. `research/archive/` 11 份 v1 评估报告 — **保留但折叠**

新用户绝大多数不会看，但**对维护者**是宝贵的"为什么 v2 长这样"的决策日志（v1 7 轮迭代试过的方向、何处翻车）。README.md line 47 / line 188-189 已经用脚注形式藏到底部，没出现在主流程。占的盘空 < 200KB，不影响 clone 体验。**留**。

### C3. `docs/decisions.png`（277 KB） — **删**

`grep` 全仓库未找到任何 markdown / HTML / shell 引用此文件（README 只引 hero.png 和 preview.png）。是 v1 时期的 demo 截图，v2 完全不用。是**纯死资源**。建议删。

---

## D. SHIP 准备度

**SHIP 前必修（3 条以内）**：

1. **`examples/sample.html:977` 删 / 改 `// 见 scripts/render.py::mermaid_text 注释。`**——单行修改，5 秒。否则 agent 抄出来的报告都会带这条 broken 引用。
2. **`docs/decisions.png` 删**——死资源，留着会让 reviewer 怀疑 docs/ 是不是漏更新。
3. （可选）`SKILL.md` 视觉规范段加一句"如果在 sample.html 看到指向 `scripts/` 的注释，忽略它"——B1 修了之后此条作废。

修完上面两条即可 ship。文档、安装、兼容性、安全规范均已就位；简化在 A1/A3/A4 都过线，A2 的 visual drift 属于长期跟踪项不阻塞 PoC 发布。

---

## 结论

**NEED FIX**（仅 2 条机械修正，<1 分钟工作量）。
修复后即可 SHIP v2 lite。
