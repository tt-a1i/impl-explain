# Brainstorm: Agent 开发后实施方案可视化

**日期**: 2026-05-11
**参与者**: shaokun.tu + Claude (Opus 4.7, 1M context)
**状态**: 探讨阶段，未实施
**触发来源**: 在 `global-hotspot-globe` 仓库做 GDELT GKG / 统一 source sync 改造时引出的元工具想法

---

## 0. TL;DR

- **问题**: AI agent 开发速度极快，人来不及关注代码细节、设计方案、实现方案。代码细节人可以不看，但**实施方案 / 架构决策**必须知道（要跟团队同步、对齐、解释为什么这么做）。
- **现状痛点**: 开发完后向 agent 询问技术细节不直观、不好理解。plan 文件 (`docs/superpowers/plans/*.md`) 是适合 agent 执行的长 markdown，不适合人 30 秒 grok。
- **方向**: 加一个 slash command，结合 skill，在开发完后生成一份**单文件 HTML**，帮助开发者直观理解实施方案、架构决策。
- **第一版选型**: 单文件 HTML（不是 React 项目，不持久化），定位是"快照"，每次开会前临时跑一次。
- **内容聚焦**: 叙事，不是代码 diff。决策、权衡、风险、架构图。
- **下一步**: 拿 `2026-05-11-unified-source-sync-manager.md` 做一份 demo HTML 验证效果，再决定要不要做成 skill。

---

## 1. 起因

Agent (Claude Code / Codex 等) 开发速度极快，快到人来不及关注代码细节、设计方案、实现方案。

- **代码细节**: 由 agent 主导没问题，人随时 `git diff` / `grep` / 问 agent 也能拿到
- **实施方案 / 架构决策**: 人**必须**知道 —— 要跟团队同步、对齐、解释为什么这么做

现状：开发完后向 agent 询问技术细节，不直观、不好理解。

---

## 2. 讨论收敛过程

### 2.1 第一轮：问题确认 + 方向

问题真实：信息存在（plan 文件、commit），但呈现方式没给人优化。plan 文件适合 agent 执行，不适合人快速 grok。

三个可能方向（按投入从小到大）：

1. **轻量**: `/explain` skill 读 plan + 关键 commit + 当前文件结构，输出单页 HTML
2. **中度**: plan 模板强制加 `## Architecture Diagram` 段落（mermaid），agent 写 plan 时必须画
3. **重度**: 本地小 web app，索引所有 plan，做跨 PR 链接（"这个 PR 改了哪些文件 / 命中了哪个 plan 的哪一步"）

**倾向方向 1**，不持久化 HTML —— 每次开会前临时跑一次，代码是事实源头，plan 是导航地图。这样不会出现"文档和代码不一致"的老问题。

### 2.2 第二轮：单文件 HTML vs React 项目

HTML 的表达优势：mermaid（流程图/时序图/类图/状态图）、Plotly/Chart.js（柱状图、桑基图、依赖图）、内嵌 CSS 颜色编码、Prism syntax highlighting，单文件就能塞下非常多东西。

**选型对比**：

| 消费场景 | 推荐 |
| --- | --- |
| 一次性看完即用（看完这次 PR 怎么搞的） | **单文件 HTML** ✓ |
| 持续浏览 + 跨 plan 对比 + 搜索（团队级"最近 10 个大改动地图"） | React app |

**第一版做单文件 HTML，理由**：

1. 验证"agent 总结的实施方案是否真有人看 + 看完是否真对齐了"这个核心假设便宜
2. 单文件 = 天然快照，跟"每次开会前临时跑一次"语义对齐
3. 零依赖：双击打开、塞进 Slack/邮件就走、不用 serve、不用维护
4. 真有跨 plan 浏览需求再升级 React，但要面对索引、改名、合并的复杂度阶跃

**关键非技术问题 —— 信息源**：

HTML 再好看，如果 agent 只是把 plan + diff 重新排版一次，价值就薄。真正值钱的是**只存在于实施当时**的信息：

- 为什么选 A 不选 B
- 什么风险被显式接受了
- 什么测试没覆盖
- 什么是故意 out-of-scope

所以设计分两段：

1. **plan 模板加结构化字段**（Decisions / Alternatives / Risks / Out-of-scope）—— 让 agent 写 plan 时被迫记录
2. **`/explain` skill** 读 plan + 实际 commits/diff，渲染成单文件 HTML

### 2.3 第三轮：HTML 内容范围

用户明确：**代码细节不重要**（随时 `git diff` / `grep`），HTML 聚焦**方案的阐释**。

#### 提议的 HTML section 结构（按读者扫一眼的优先级排序）

1. **TL;DR 卡片**
   - 一句话目标
   - 一句话采用方案
   - 一句话核心权衡
   - 开会拿出来 30 秒能讲完那种

2. **架构图**（HTML 比 markdown 强的核心战场）
   - mermaid 流程图或组件图
   - 标清新组件 vs 已有组件的不同颜色

3. **决策记录**（ADR 卡片样式）
   - 每张卡片：问题 / 选了什么 / 拒了什么备选 / 理由 / 已知代价
   - 颜色 tag 标 `chosen` / `rejected` / `deferred`

4. **数据流 before/after**
   - 两张并排的 mermaid
   - 让人一眼看到"以前 A→B→C，现在 A→D→B→C"

5. **风险与 out-of-scope**
   - 哪些事故意没做
   - 哪些边界条件没覆盖
   - 哪些假设如果破了会出问题

6. **文件地图（无代码）**
   - 一个表：新建 / 改 / 删 + 文件 + 一句话职责
   - 点击跳 IDE，但**不嵌代码、不贴 diff、不放 signature**

#### 关于"代码痕迹"的边界

唯一保留的代码引用是**文件地图**，作为导航锚点 —— 团队成员看完叙事后想自己 grep 时，得知道从哪入手。但表里纯文字职责说明，零代码内容。

---

## 3. 下一步行动建议

**Demo 验证**：拿当前 `global-hotspot-globe` 仓库的 `docs/superpowers/plans/2026-05-11-unified-source-sync-manager.md` 做一份 demo HTML。

理由：
- 这个 plan 刚做完
- 决策点清晰（注册表 + 调度器 + 抑制 legacy loop）
- 适合验证"剥掉代码后纯叙事 HTML 是不是真够用"

效果出来后再决定是否做成 `/explain` skill。

---

## 4. 待定 / 开放问题

| 问题 | 备注 |
| --- | --- |
| HTML 里的 mermaid 图谁画 —— agent 现场推断 vs plan 模板强制提供? | 关系到信息源稳定性 |
| 颜色 tag / 卡片样式要不要做成可主题切换? | YAGNI 风险，第一版可能不需要 |
| 文件地图的"一句话职责"来源 —— agent 现场看代码生成 vs plan 里强制填? | 影响生成结果的可重复性 |
| 跨 plan 链接什么时候考虑? | 暂定到 React app 阶段再处理 |
| HTML 里要不要嵌 git log / commit 时间线? | 待定，可能作为可选 section |
| 第一版是 standalone HTML 还是依赖 CDN (mermaid.js / prism)? | 倾向 CDN，足够轻量；离线场景再考虑 inline |

---

## 5. 核心约束 / 价值锚

写给未来接续的 agent 或我自己：

1. **第一版不持久化 HTML**：每次跑都重新生成，避免"文档腐烂"
2. **代码不是焦点**：reviewer 想看 diff 自己 `git show`
3. **叙事 + 决策 + 权衡 > 完整性**：信息密度比覆盖度重要
4. **演进路径**: 单文件 HTML → 验证有人用 → 再决定升级 React 站点
5. **plan 模板和 skill 是两个分开的工件**：可以独立演进，但 skill 依赖 plan 提供结构化字段
6. **skill 跨 agent 通用**：独立 skill，不绑死 superpowers 体系，Claude Code / Codex / opencode 都能加载使用。这意味着：
   - 标准 markdown + frontmatter（`name` / `description` / body），不依赖任何家专属 schema
   - 指令里只引用通用能力（读文件 / 写文件 / 跑 shell），不写 Claude-only 的工具调用语法
   - HTML 产出方式：让 agent **直接生成 HTML 字符串写盘**，不依赖某家特定的代码执行环境，最大化可移植性
   - 安装方式应该简单：`git clone` 或 `curl` 拿到 skill 文件后，按各 agent 的 skill 加载约定放置即可

---

## 6. 项目命名 / 定位

- 项目目录: `/Users/admin/code/impl-explain/`
- 关键产出物（未来）:
  - `/explain` slash command
  - 配套 skill（读 plan + commit/diff，渲染单文件 HTML）
  - plan 模板增强（Decisions / Alternatives / Risks / Out-of-scope 字段）
  - demo HTML（验证用，基于 unified-source-sync-manager plan）
