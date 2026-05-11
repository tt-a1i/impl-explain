# impl-explain Implementation Plan

> 对接续 agent / 后续维护者：本 plan 是事实源头之一，但代码冲突时信代码并立刻更新本文档。

**日期**: 2026-05-11
**项目**: `/Users/admin/code/impl-explain/`
**前置文档**:
- 起因 / 思路收敛：`../../2026-05-11-brainstorm.md`
- 三家 skill 格式调研：`../../research/2026-05-11-cross-agent-skill-survey.md`

---

## 0. Goal

做一个跨 agent 的 skill（Claude Code / Codex / opencode 通用），在 AI agent 完成实现任务后，读项目里的 plan 文件 + git log/diff，生成一份**单文件 HTML 实施报告**，把方案 / 决策 / 架构图 / 风险用图表+颜色呈现给团队成员。

## 1. Architecture（高层）

```
plan markdown + git context
        │
        ▼
   ┌─────────────┐
   │ SKILL.md    │  (纯叙事 markdown 指令)
   │ agent 读     │
   └──────┬──────┘
          │ agent 综合成 JSON
          ▼
   ┌──────────────────────┐
   │ scripts/render.py    │  (Python 3 stdlib)
   │ JSON → HTML          │
   └──────┬───────────────┘
          ▼
   impl-explain.html  (单文件, 内嵌 mermaid CDN)
```

## 2. Tech Stack

- Python 3 标准库（不依赖任何 pip 包）
- Mermaid via CDN（`unpkg.com/mermaid@11`）
- 纯 SKILL.md，不用 Claude 专有 frontmatter 字段
- 不用模板引擎（Jinja2 等），用 string format 拼接

## 3. Project File Structure

```
/Users/admin/code/impl-explain/
├── 2026-05-11-brainstorm.md           # ✅ 已存在
├── README.md                          # 三家安装说明 + 用法 + 设计哲学
├── SKILL.md                           # 主 skill 文件（frontmatter + 叙事 body）
├── install.sh                          # 一键安装到三家
├── scripts/
│   └── render.py                       # JSON → HTML 渲染器
├── templates/
│   └── plan-template.md                # PLAN_TEMPLATE.md（结构化字段建议）
├── slash-wrappers/
│   ├── codex-prompt.md                 # ~/.codex/prompts/impl-explain.md
│   └── opencode-command.md             # ~/.config/opencode/commands/impl-explain.md
├── docs/
│   └── plan/
│       └── 2026-05-11-implementation-plan.md  # 本文档
├── research/
│   └── 2026-05-11-cross-agent-skill-survey.md  # ✅ 已存在
└── examples/
    ├── unified-source-sync-manager.input.json  # demo 输入
    └── unified-source-sync-manager.html        # demo 产出
```

## 4. Tasks

### Task A: render.py — JSON schema 定义 + 核心渲染

**File**: `scripts/render.py`

#### A.1 输入 JSON schema

```python
{
  "meta": {
    "title": str,
    "date": str,           # ISO 日期
    "plan_file": str,      # 相对路径
    "git_range": str       # 比如 "main..HEAD"
  },
  "tldr": {
    "goal": str,
    "approach": str,
    "tradeoff": str
  },
  "architecture_diagram": {
    "type": "mermaid",
    "diagram": str         # mermaid 源码
  } | None,
  "data_flow": {
    "before": str,         # mermaid
    "after": str           # mermaid
  } | None,
  "decisions": [
    {
      "question": str,
      "chosen": str,
      "rejected": [str],
      "rationale": str,
      "cost": str,
      "status": "chosen" | "rejected" | "deferred"
    }
  ],
  "risks": [
    {
      "description": str,
      "severity": "low" | "medium" | "high",
      "mitigated": bool,
      "note": str | None
    }
  ],
  "out_of_scope": [str],
  "files": [
    {
      "path": str,
      "change_type": "new" | "modified" | "deleted",
      "responsibility": str
    }
  ]
}
```

#### A.2 CLI

```
python3 render.py --input <path.json> --output <path.html>
# 或
python3 render.py < input.json > output.html
```

默认输出到 `$CWD/impl-explain.html`，输入支持 stdin 或 `--input`。

#### A.3 校验

- 字段类型基础校验（不依赖 pydantic）
- 校验失败：打印有意义的错误到 stderr，退出码非 0
- meta 必填；其他段缺失则跳过对应 HTML section

### Task B: HTML 模板 + 视觉

集成在 `render.py` 内部（不抽外部模板文件）。

**6 段结构**（已在 brainstorm doc 锁定）:
1. TL;DR 卡片
2. 架构图（mermaid）
3. 决策记录卡片
4. 数据流 before/after（并排 mermaid）
5. 风险 + out-of-scope
6. 文件地图

**视觉规范**:
- 暗色主题（团队成员看屏幕舒服）
- 配色: chosen 绿 / rejected 红 / deferred 黄；severity high 红 / medium 黄 / low 灰；change_type new 绿 / modified 蓝 / deleted 红
- 卡片式布局，间距充足
- mermaid 主题: `default` 或 `dark`
- 字体: system font stack

### Task C: Demo HTML（验证视觉）

**输入源**: `global-hotspot-globe` 仓库的 `docs/superpowers/plans/2026-05-11-unified-source-sync-manager.md` + 当前分支的 commit。

**步骤**:
1. 手工生成 `examples/unified-source-sync-manager.input.json`
2. 跑 `python3 scripts/render.py --input examples/...json --output examples/...html`
3. 打开 HTML 检查

**验收**:
- 在浏览器双击打开正常
- mermaid 图渲染正确
- 颜色编码可见
- 在 1280×800 屏幕上排版良好

### Task D: SKILL.md（cross-agent 主体）

**File**: `SKILL.md`

**frontmatter**:
```yaml
---
name: impl-explain
description: 在实现工作做完后，把项目的 implementation plan + git diff/log 渲染成一份单文件 HTML 实施报告，包含 TL;DR、架构图、决策记录、风险清单和文件地图。适合开会前快速对齐团队成员。当用户说 "生成实施报告"、"impl-explain"、"explain implementation"、"展示这次实施方案" 时调用。
---
```

**body 关键约束**:
- 不点名 Read / Bash / Write 任何家的工具名
- 用动词叙事："读取 X"、"运行 git X"、"调用 scripts/render.py"
- 步骤化：找 plan → 提取结构化信息 → 跑 git 拿上下文 → 综合 JSON → 调 render.py → 报告路径

**body 草稿** 详见 Task D.1。

### Task E: Slash 壳子（Codex / opencode）

Claude Code 自动有 `/impl-explain`，零工作。

**File 1**: `slash-wrappers/codex-prompt.md`
- 内容: 让 Codex 调用 impl-explain skill 的简短指令
- 安装路径: `~/.codex/prompts/impl-explain.md`

**File 2**: `slash-wrappers/opencode-command.md`
- 内容: 让 opencode agent 调用 impl-explain skill
- 安装路径: `~/.config/opencode/commands/impl-explain.md`

### Task F: install.sh

**目标**: 一行命令把所有部分安装到正确位置。

**功能**:
- 把 SKILL.md + scripts/ 复制（或 symlink）到 `~/.agents/skills/impl-explain/`
- symlink `~/.claude/skills/impl-explain/` → `~/.agents/skills/impl-explain/`
- 复制 `slash-wrappers/codex-prompt.md` → `~/.codex/prompts/impl-explain.md`
- 复制 `slash-wrappers/opencode-command.md` → `~/.config/opencode/commands/impl-explain.md`
- 报告每一步成功/跳过

**安全**:
- 已存在则提示是否覆盖（默认 No，需 `--force`）
- mkdir -p 父目录

### Task G: README.md

**Sections**:
1. 项目目的（一段）
2. Quick install（一行 curl 或 git clone + install.sh）
3. 三家用法
   - Claude Code: 输入 `/impl-explain`
   - Codex: `/skills` 选 impl-explain，或 `/impl-explain`（fallback）
   - opencode: 输入 `/impl-explain` 或让 agent 主动调
4. 输出长什么样（截图位置占位）
5. 设计哲学（链到 brainstorm 文档）
6. 已知限制 / 兼容性矩阵
7. Roadmap（未来 React 站点）

### Task H: PLAN_TEMPLATE.md

**File**: `templates/plan-template.md`

让 plan 作者（人或 agent）写 plan 时被迫记录"只存在于实施当时"的信息：
- Goal
- Architecture
- **Decisions**（结构化字段，render.py 直接消费）
- **Alternatives Considered**
- **Risks**
- **Out-of-scope**
- Tasks

附一段说明：本模板与 impl-explain skill 配套使用，按这个结构写 plan，agent 提取 JSON 时几乎无需推断。

## 5. 验证标准

### 端到端 smoke test

1. 在 `~/.claude/skills/impl-explain/` 装好后，在 `global-hotspot-globe` 仓库里跑 `/impl-explain`，能产出非空 HTML
2. HTML 在浏览器打开，6 段全部存在
3. mermaid 图渲染（不显示原始文本）
4. 颜色 tag 显示正确

### 兼容性验证

- Codex / opencode 真机暂不验证（用户后续可以实测）
- 但 SKILL.md 不能含任何 Claude 专有标记（grep `\${CLAUDE_SKILL_DIR}`、`` !`cmd` ``、`$ARGUMENTS` 全部为 0）

### 文件清单核对

```bash
# 必须存在
test -f /Users/admin/code/impl-explain/SKILL.md
test -f /Users/admin/code/impl-explain/scripts/render.py
test -f /Users/admin/code/impl-explain/install.sh
test -f /Users/admin/code/impl-explain/README.md
test -f /Users/admin/code/impl-explain/templates/plan-template.md
test -f /Users/admin/code/impl-explain/slash-wrappers/codex-prompt.md
test -f /Users/admin/code/impl-explain/slash-wrappers/opencode-command.md
test -f /Users/admin/code/impl-explain/examples/unified-source-sync-manager.input.json
test -f /Users/admin/code/impl-explain/examples/unified-source-sync-manager.html
```

## 6. Execution Order

按依赖：

1. **render.py + 内嵌模板** —— 端到端骨架先建好
2. **Demo input JSON + 产出 HTML** —— 用真实 plan 验证视觉
3. **SKILL.md** —— 调研约束已明，照写即可
4. **Slash wrappers** —— 短小，最后两个文件
5. **install.sh** —— 拼装上面所有产物
6. **README + PLAN_TEMPLATE** —— 文档收尾

## 7. 风险与已知约束

| 风险 | 处理 |
| --- | --- |
| Codex skills 在 `/skills` 菜单里 description 字符上限严，被截断后触发不到 | description 控制在 1000 字符内，关键触发词放前 200 字符 |
| `${CLAUDE_SKILL_DIR}` 等 Claude 专属占位符潜在误用 | SKILL.md 写完后 grep 兜底 |
| 用户没装 Python 3 | 极少见（macOS / Linux 默认有）；install.sh 跑前检测 `python3 --version` |
| Mermaid CDN 离线场景挂掉 | v1 不解决；README 标"需网络"，未来用 inline mermaid.min.js 解决 |
| plan markdown 没结构化字段时，agent 推断质量不稳定 | PLAN_TEMPLATE 引导，render.py 对缺失字段优雅降级（跳过对应 section） |
