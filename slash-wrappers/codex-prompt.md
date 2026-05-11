---
description: 调用 impl-explain skill 把当前 plan + git 变更渲染成单文件 HTML 实施报告
argument-hint: [可选 plan 路径]
---

<!--
  注意：本壳子文件放在 ~/.codex/prompts/ 下，依赖 Codex custom prompts 机制。
  该机制已被官方标记为 deprecated（参见 https://developers.openai.com/codex/custom-prompts）。
  长期方案是让用户走 `/skills` 菜单或 `$impl-explain` mention 触发原生 skill。
  本文件作为 fallback 让 `/impl-explain` 在 Codex 当前版本仍能直接触发。
-->

请按下面的步骤生成本次实施的 HTML 报告。

1. 找到 impl-explain skill 的 SKILL.md。优先级路径：
   - `~/.codex/.agents/skills/impl-explain/SKILL.md`
   - `~/.agents/skills/impl-explain/SKILL.md`
   - `~/.claude/skills/impl-explain/SKILL.md`

   第一个存在的即用。如果都找不到，告诉用户先跑 `./install.sh` 安装 skill。

2. 加载该 SKILL.md 的内容，按其中的"执行步骤"1-6 步逐步执行。

3. 用户参数：`$ARGUMENTS`（如果非空，作为 plan 文件路径优先使用；如果为空，按 SKILL.md 步骤 1 自动定位）。

不要跳过任何一步。HTML 是叙事不是 changelog。
