<div align="center">

**中文** · [English](README.en.md)

# impl-explain

**Cross-agent skill for one-page HTML implementation reports**

把"刚做完的实施 + git 历史"渲染成一份**单文件 HTML 叙事报告**。
开会前 30 秒发到 Slack，团队读 60 秒对齐"做了什么 / 为什么这么做 / 有什么风险"。

<br>

[![Agents](https://img.shields.io/badge/Agents-Claude_Code_·_Codex_·_opencode-b04a1f)](#compatibility)
[![Prompt-only](https://img.shields.io/badge/Prompt--only-no_code_runtime-4a6a2c)](#how-it-works)
[![Status](https://img.shields.io/badge/Status-v2_lite-555)](#roadmap)

[Install](#install) · [Usage](#usage) · [What you get](#what-you-get) · [Why](#why-this-exists)

</div>

<br>

![preview](docs/hero.png)

---

## Why this exists

AI agent 写代码极快——快到团队成员根本来不及看清实施方案、架构、决策。

代码细节随时 `git diff` 拿得到。但**只存在于实施当时**的信息呢？

- 你为什么选 A 不选 B
- 哪些事**故意没做**
- 哪些事**可能出问题**

`impl-explain` 把这些信息从 plan + git context 里抽出来，渲染成一份单文件 HTML——
**不是 changelog，不是 dashboard，是叙事。**

## How it works

**Prompt-only skill — 没有 Python 脚本、没有 JSON schema、没有 validator**。

Agent 读 `SKILL.md`（指令）+ `examples/sample.html`（视觉参考），然后直接生成 HTML 写到磁盘。一致性靠 sample.html 当 anchor，质量靠 SKILL.md 里的检查清单。

> 历史版本：v1 走 JSON schema + `render.py` 渲染管线，迭代到第 7 轮后认定"过度设计"。v1 标签：`v1-structured-2026-05-11`，旧评估报告在 [`research/archive/`](research/archive/)。

## What you get

每份 HTML 报告大致包含（缺什么跳什么，**不硬凑**）：

| Section | 内容 |
| --- | --- |
| **Hero** | 衬线大标题 · 副标题 · 1-3 个 metric chip · plan path · commits 折叠 |
| **TL;DR** | 三行：**做什么 / 怎么做 / 代价**（整体账）+ 尾部风险预告 + → Risks 锚 |
| **Architecture** | Mermaid 流程图 · 可选上方 summary 叙述 · 下方 caption 颜色编码说明 |
| **Before / After** | 数据流改动前后并排对比（mermaid）|
| **Decisions** | 编号决策卡片：结论式短标题 · 采用 / 理由 / 放弃 / 代价 · `chosen` 或 `deferred` |
| **Risks** | 风险列表 · 顶部 snapshot · Top risk inline highlight · severity 染色 · mitigation 三态 |
| **Out of Scope** | 故意没做的事 |
| _顶部_ | sticky TOC（6 锚点）+ 滚动 progress bar |

视觉风格：**浅色编辑风**（warm cream + Fraunces 衬线 + Inter 正文 + JetBrains Mono 标签），不是 dashboard。

完整样例 → [`examples/sample.html`](examples/sample.html)（git clone 后直接双击）。

<details>
<summary>预览完整报告（点击展开）</summary>

<br>

![full preview](docs/preview.png)

</details>

## Install

### 一行装好

```bash
git clone https://github.com/tt-a1i/impl-explain.git
cd impl-explain
./install.sh
```

安装会把 `SKILL.md` + `examples/sample.html` copy 到四个位置覆盖三家 agent。Claude Code 自动暴露 `/impl-explain`。

### 开发模式（symlink）

```bash
./install.sh --link
```

目标位置 symlink 到源仓库——源改了立即生效。

### 其他命令

```bash
./install.sh --force        # 覆盖已存在的安装
./install.sh --no-wrappers  # 只装 skill, 不装 Codex/opencode 壳子
./install.sh --uninstall    # 移除所有安装位置
./install.sh --help
```

## Usage

实施工作做完后（plan 写好 · 代码 commit），在 agent 会话里：

| Agent | 触发 | 备注 |
| --- | --- | --- |
| **Claude Code** | `/impl-explain` | 原生 slash，零配置 |
| **Codex CLI** | `/impl-explain` 或 `/skills` 菜单 | Custom prompts 是 fallback（已被官方标 deprecated）|
| **opencode** | `/impl-explain` | Commands 壳子先尝试原生 `skill()` 工具，失败再读文件 |

可选参数：plan 文件路径。例：`/impl-explain docs/plans/2026-05-11-foo.md`。

Agent 会：

```
1. 找到 plan 文件 ─ 多 plan 仓库用 commit 关键词交叉验证, 必要时问用户
2. 跑 git log + git diff --name-status 收集 commits
3. 读 examples/sample.html 当视觉参考, 直接生成 HTML 写到项目根
4. 把绝对路径告诉你
```

HTML 输出到 `git rev-parse --show-toplevel` 算出的项目根 `impl-explain.html`，**默认不 commit**。

## Plan template tip

最简单提升报告质量的方式：写 plan 时用 [`templates/plan-template.md`](templates/plan-template.md) 的结构。

模板字段（TL;DR / Architecture / Data Flow / Decisions / Risks / Out of Scope / Metrics）与报告 section **一一对应**——agent 提取时几乎无需推断。模板含 **4 个反例**防踩坑。

## Compatibility

| 项 | Claude Code | Codex CLI | opencode |
| --- | --- | --- | --- |
| skill 自动发现 | ✓ | ✓ | ✓ |
| `/impl-explain` slash 直接触发 | ✓ 原生 | ✓ prompts 壳子（fallback）| ✓ commands 壳子 |
| description 字符上限 | 1536 | ~1000 | 1024 |

description 控制在 1000 字符内，三家都安全。

**已知限制**：

- **Mermaid CDN 需要联网**——离线场景目前不支持
- **风格统一靠 sample.html anchor**——如果 sample 被替换，新报告会跟着变（这是 v2 的 feature 不是 bug：换风格只改 sample）

## Design philosophy

> **HTML 是叙事，不是 changelog。**
>
> 读者已经能 `git diff` 看代码改动，但看不到：你为什么选 A 不选 B / 哪些事故意没做 / 哪些事可能出问题。
>
> 这份 skill 把 agent 注意力推到那三类信息上。**没有 schema 强制**，靠 prompt 引导 + sample.html anchor + 反例。**文件地图段刻意没有**——reviewer 想看哪些文件改了，自己 `git diff --name-status` 一行命令。

## Roadmap

- **v2 lite（当前）** — 纯 prompt skill + sample.html anchor，无 Python runtime
- v1 structured（已归档）— JSON schema + render.py，tag `v1-structured-2026-05-11`，用 `git checkout` 可恢复
- v3 候选 — sample.html 内嵌 mermaid.min.js（离线可看）
- v4 候选 — 多 sample 主题（编辑风 / dashboard 风 / 极简风），让用户选

## Project structure

```
impl-explain/
├── README.md / README.en.md    # 中英文 README
├── SKILL.md                    # 主 skill 文件（prompt-only）
├── install.sh                  # 一键安装到三家
├── examples/
│   └── sample.html             # 视觉参考样例（agent 必读）
├── templates/
│   └── plan-template.md        # 配套 plan 写作模板 + 4 反例
├── slash-wrappers/
│   ├── codex-prompt.md         # → ~/.codex/prompts/impl-explain.md
│   └── opencode-command.md     # → ~/.config/opencode/commands/impl-explain.md
├── docs/
│   ├── hero.png / preview.png  # README 用截图
│   └── plan/                   # 本项目自身的 plan
└── research/archive/           # v1 时期 11 份评估报告（迭代设计参考）
```

---

<div align="center">
<sub>v1 经 7 轮多角度子代理评估迭代后，因"过度设计"在 v2 lite 简化。<br>
v1 评估报告归档在 <a href="research/archive/">research/archive/</a>。</sub>
</div>
