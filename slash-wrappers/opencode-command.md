---
description: 调用 impl-explain skill 把当前 plan + git 变更渲染成单文件 HTML 实施报告
---

请生成本次实施的 HTML 报告。**优先**使用 opencode 原生 `skill` 工具调用，**仅在失败时**回落到手动读 SKILL.md。

## 优先路径（原生 skill 工具）

调用 opencode 原生工具：

```
skill({ name: "impl-explain" })
```

如果工具调用成功并加载了 SKILL.md，按 SKILL.md "执行步骤"1-6 步执行。

## Fallback 路径（手动加载 SKILL.md）

如果 `skill({name: "impl-explain"})` 不可用（工具找不到 / 报 unknown skill），按以下优先级查找文件：

- `~/.config/opencode/skills/impl-explain/SKILL.md`
- `~/.claude/skills/impl-explain/SKILL.md`
- `~/.agents/skills/impl-explain/SKILL.md`

读取第一个存在的 SKILL.md，按其中"执行步骤"1-6 步执行。

如果都没找到：告诉用户先跑 `./install.sh` 安装 skill，然后停止。

## 通用注意事项

- 不要跳过任何一步
- HTML 是叙事不是 changelog——决策、权衡、风险才是重点，不是代码 diff
- 如果用户在命令后跟了 plan 路径参数，作为步骤 1 的指定路径优先使用
