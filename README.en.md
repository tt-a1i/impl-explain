<div align="center">

[中文](README.md) · **English**

# impl-explain

**Cross-agent skill for one-page HTML implementation reports**

Render "what you just shipped + git history" into a single-file HTML narrative.
Drop it in Slack 30 seconds before the meeting — your team aligns in 60 seconds on
"what was done / why this way / what could break".

<br>

[![Python 3.x](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![Agents](https://img.shields.io/badge/Agents-Claude_Code_·_Codex_·_opencode-b04a1f)](#compatibility)
[![No pip deps](https://img.shields.io/badge/Dependencies-stdlib_only-4a6a2c)](#install)
[![Status](https://img.shields.io/badge/Status-v1_ready-555)](#roadmap)

[Install](#install) · [Usage](#usage) · [What you get](#what-you-get) · [Why](#why-this-exists)

</div>

<br>

![preview](docs/hero.png)

---

## Why this exists

AI agents write code blazingly fast — too fast for the team to keep up with implementation plans, architecture decisions, design rationale.

Code details are always one `git diff` away. But the stuff that **only exists at implementation time**?

- Why you picked A over B
- What you **deliberately didn't do**
- What **might break later**

`impl-explain` extracts these from your plan + git context and renders a single-file HTML —
**not a changelog, not a dashboard. A narrative.**

## What you get

Each report contains the following structure (missing sections are gracefully skipped):

| Section | Content |
| --- | --- |
| **Hero** | Serif title · subtitle · 1-3 metric chips · plan path · collapsible commits |
| **TL;DR** | 3 rows: **what / how / tradeoff** (overall cost, not per-decision detail) |
| **Risk preview** | Tail line in TL;DR + → Risks jump anchor |
| **Architecture** | Mermaid flowchart · optional summary above · optional caption below |
| **Before / After** | Side-by-side mermaid showing data-flow change |
| **Decisions** | Numbered cards: declarative title · chosen / rationale / rejected / cost · `chosen` or `deferred` |
| **Risks** | List with top snapshot · inline highlight for top risk · severity color · 3-state mitigation |
| **Out of Scope** | Things deliberately not done |
| _top_ | Sticky TOC (6 anchors) + scroll progress bar |

Visual style: **light editorial** (warm cream + Fraunces serif + Inter body + JetBrains Mono labels). Not a dashboard.

Full sample → [`examples/unified-source-sync-manager.html`](examples/unified-source-sync-manager.html) (clone + double-click).

<details>
<summary>Preview the full report (click to expand)</summary>

<br>

![full preview](docs/preview.png)

</details>

## Install

### One-line install

```bash
git clone https://github.com/tt-a1i/impl-explain.git
cd impl-explain
./install.sh
```

Deploys the skill to four locations covering all three agents, and writes `~/.config/impl-explain/manifest.json` so the skill is **reachable from any repo**. Claude Code auto-exposes `/impl-explain` — no extra setup.

### Dev mode (symlink)

```bash
./install.sh --link
```

Target locations symlink to the source repo — edits go live immediately.

### Other commands

```bash
./install.sh --force        # overwrite existing install (after source edits)
./install.sh --status       # check the 4 copies for drift against source
./install.sh --uninstall    # remove all install locations
./install.sh --help
```

> **Copy-mode staleness reminder**: in default copy mode, the 4 installed copies are independent. After modifying the source repo, re-run `./install.sh --force`, or the copies won't update. Use `--status` to detect drift anytime.

## Usage

When implementation is done (plan written · code committed), in your agent session:

| Agent | Trigger | Note |
| --- | --- | --- |
| **Claude Code** | `/impl-explain` | Native slash, zero config |
| **Codex CLI** | `/impl-explain` or `/skills` menu | Custom prompts are a fallback (deprecated by Codex) |
| **opencode** | `/impl-explain` | Commands wrapper tries native `skill()` first, falls back to reading the file |

Optional argument: plan file path. Example: `/impl-explain docs/plans/2026-05-11-foo.md`.

The agent will:

```
1. Find the plan file (cross-validates via commit keywords in multi-plan repos)
2. Run git log + git diff --name-status to collect commits
3. Synthesize the JSON
4. Call render.py
5. Tell you the absolute HTML path
```

HTML is written to `git rev-parse --show-toplevel`/`impl-explain.html`. **Not committed by default**.

## Plan template tip

Easiest way to improve report quality: write your plan using the structure in [`templates/plan-template.md`](templates/plan-template.md).

Template sections (TL;DR / Architecture / Data Flow / Decisions / Risks / Out of Scope / Metrics) map **field-by-field** to the JSON schema — the agent extracts almost nothing through inference.

The template includes **4 anti-patterns** (Decision writing, Risk writing, Out-of-Scope writing, TL;DR.tradeoff vs Decision.cost distinction) to avoid common traps.

## Compatibility

| Item | Claude Code | Codex CLI | opencode |
| --- | --- | --- | --- |
| Skill auto-discovery | ✓ | ✓ | ✓ |
| `/impl-explain` direct slash | ✓ native | ✓ prompts wrapper (fallback) | ✓ commands wrapper |
| Description char limit | 1536 | ~1000 | 1024 |
| Default sandbox `find` fallback | ✓ | ✗ (uses explicit paths + manifest) | ✓ |

Description stays under 1000 chars — safe for all three.

**Known limitations**:

- **Mermaid CDN requires internet** — offline rendering not supported yet
- **Single-process rendering** — cross-plan browsing / indexing not in v1
- **Multi-replica deploys** — the manifest is a local file; CI containers need their own install

## JSON Schema

<details>
<summary>Expand full schema (agent-internal)</summary>

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
    {"title", "chosen", "rejected[]", "rationale", "cost?", "status"}
  ],
  "risks": [
    {"description", "severity", "mitigation", "note?"}
  ],
  "out_of_scope": [string]
}
```

**Enums and hard constraints** (enforced by `validate()`):

- `decisions[].status` ∈ `chosen` / `deferred` (`rejected` is deprecated — belongs in `out_of_scope`)
- `risks[].severity` ∈ `low` / `medium` / `high`
- `risks[].mitigation` ∈ `full` / `partial` / `none` (legacy `mitigated: bool` still accepted)
- `decisions[]` must have ≥ 1 entry
- `risks[]` must have ≥ 1 entry
- mermaid strings must start with `flowchart` / `graph` / `sequenceDiagram` etc (so ASCII art can't silently break the HTML)

Full schema in [`scripts/render.py`](scripts/render.py) `validate()`.

</details>

## Customize visuals

<details>
<summary>Expand visual-customize guide</summary>

Edit the `CSS` and `JS` constants at the top of [`scripts/render.py`](scripts/render.py):

- **Color tokens** live in CSS `:root` — change the palette in one place
- **Mermaid theme** in the `JS` `themeVariables` object
- **Fonts** in the `@import url('https://fonts.googleapis.com/...')` line

To add/remove fields: edit `validate()` and the matching `render_*()` function. Don't forget to sync the JSON schema in [`SKILL.md`](SKILL.md).

</details>

## Design philosophy

> **The HTML is a narrative, not a changelog.**
>
> Readers already know what code changed (`git diff`). What they can't see: why you picked A over B / what you deliberately didn't do / what might break.
>
> This skill forces the agent to extract those three things into **structured fields**. If the info is thin, `validate()` enforces hard rules: `decisions ≥ 1`, `risks ≥ 1`, mermaid syntax, etc.
>
> **No file-map section by design** — if reviewers want to see which files changed, `git diff --name-status` is one command away.

## Roadmap

- **v1 (current)** — single-file HTML, regenerated every run, no persistent index
- v2 candidate — plan-template lint (check required sections present)
- v3 candidate — local React site for cross-plan browsing + cross-PR linking
- v4 candidate — inline mermaid (no CDN, works offline)

## Project structure

```
impl-explain/
├── README.md / README.en.md    # Chinese / English README
├── SKILL.md                    # main skill file (cross-agent, pure markdown + frontmatter)
├── install.sh                  # one-line installer + --status / --uninstall / --link
├── scripts/
│   └── render.py               # JSON → HTML renderer (Python stdlib only)
├── templates/
│   └── plan-template.md        # companion plan template + 4 anti-patterns
├── slash-wrappers/
│   ├── codex-prompt.md         # → ~/.codex/prompts/impl-explain.md
│   └── opencode-command.md     # → ~/.config/opencode/commands/impl-explain.md
├── examples/
│   ├── unified-source-sync-manager.input.json   # demo input
│   └── unified-source-sync-manager.html         # demo output
├── docs/
│   ├── hero.png / preview.png  # README screenshots
│   └── plan/                   # this project's own implementation plan
└── research/                   # 6 rounds of multi-angle subagent evaluation reports
```

---

<div align="center">
<sub>Iteratively refined over 6 rounds of multi-angle subagent evaluation (visual / IA / LLM walkthrough / cross-agent). <br>
All evaluation reports in <a href="research/">research/</a>.</sub>
</div>
