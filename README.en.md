<div align="center">

[中文](README.md) · **English**

# impl-explain

**Cross-agent skill for one-page HTML implementation reports**

Render "what you just shipped + git history" into a single-file HTML narrative.
Drop it in Slack 30 seconds before the meeting — your team aligns in 60 seconds on
"what was done / why this way / what could break".

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

AI agents write code blazingly fast — too fast for the team to keep up with implementation plans, architecture decisions, design rationale.

Code details are always one `git diff` away. But the stuff that **only exists at implementation time**?

- Why you picked A over B
- What you **deliberately didn't do**
- What **might break later**

`impl-explain` extracts these from your plan + git context and renders a single-file HTML —
**not a changelog, not a dashboard. A narrative.**

## How it works

**Prompt-only skill — no Python runtime, no JSON schema, no validator**.

The agent reads `SKILL.md` (instructions) + `examples/sample.html` (visual anchor), then generates the HTML directly. Consistency is anchored by `sample.html`; quality comes from the checklists in `SKILL.md`.

> Earlier version: v1 used a JSON schema + `render.py` rendering pipeline. After 7 rounds of iteration it was retired as "over-engineered". Tag: `v1-structured-2026-05-11`. Old evaluation reports live in [`research/archive/`](research/archive/).

## What you get

Each report contains roughly the following (sections are skipped if empty — no padding):

| Section | Content |
| --- | --- |
| **Hero** | Serif title · subtitle · 1-3 metric chips · plan path · collapsible commits |
| **TL;DR** | 3 rows: **what / how / tradeoff** (overall cost) + tail risk preview + → Risks anchor |
| **Architecture** | Mermaid flowchart · optional summary above · optional caption below |
| **Before / After** | Side-by-side mermaid showing data-flow change |
| **Decisions** | Numbered cards: declarative title · chosen / rationale / rejected / cost · `chosen` or `deferred` |
| **Risks** | List with top snapshot · inline highlight for top risk · severity color · 3-state mitigation |
| **Out of Scope** | Things deliberately not done |
| _top_ | Sticky TOC (6 anchors) + scroll progress bar |

Visual style: **light editorial** (warm cream + Fraunces serif + Inter body + JetBrains Mono labels). Not a dashboard.

Full sample → [`examples/sample.html`](examples/sample.html) (clone + double-click).

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

Copies `SKILL.md` + `examples/sample.html` to four locations covering all three agents. Claude Code auto-exposes `/impl-explain`.

### Dev mode (symlink)

```bash
./install.sh --link
```

Target locations symlink to the source repo — edits go live immediately.

### Other commands

```bash
./install.sh --force        # overwrite existing install
./install.sh --no-wrappers  # skip the Codex / opencode wrappers
./install.sh --uninstall    # remove all install locations
./install.sh --help
```

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
3. Read examples/sample.html as visual reference, generate HTML directly into the repo root
4. Tell you the absolute HTML path
```

HTML is written to `git rev-parse --show-toplevel`/`impl-explain.html`. **Not committed by default**.

## Plan template tip

Easiest way to improve report quality: write your plan using the structure in [`templates/plan-template.md`](templates/plan-template.md).

Template sections (TL;DR / Architecture / Data Flow / Decisions / Risks / Out of Scope / Metrics) map **section-by-section** to the report — the agent extracts almost nothing through inference. The template includes **4 anti-patterns** to avoid common traps.

## Compatibility

| Item | Claude Code | Codex CLI | opencode |
| --- | --- | --- | --- |
| Skill auto-discovery | ✓ | ✓ | ✓ |
| `/impl-explain` direct slash | ✓ native | ✓ prompts wrapper (fallback) | ✓ commands wrapper |
| Description char limit | 1536 | ~1000 | 1024 |

Description stays under 1000 chars — safe for all three.

**Known limitations**:

- **Mermaid CDN requires internet** — offline rendering not supported yet
- **Visual consistency relies on `sample.html` as anchor** — replacing it changes all future reports (intentional; switching styles is a single-file edit)

## Design philosophy

> **The HTML is a narrative, not a changelog.**
>
> Readers already know what code changed (`git diff`). What they can't see: why you picked A over B / what you deliberately didn't do / what might break.
>
> This skill steers the agent toward those three things. **No schema enforcement** — prompt guidance + `sample.html` anchor + counter-examples. **No file-map section by design** — `git diff --name-status` is one command away.

## Roadmap

- **v2 lite (current)** — pure prompt skill + `sample.html` anchor, no Python runtime
- v1 structured (archived) — JSON schema + `render.py`, tag `v1-structured-2026-05-11`, recoverable via `git checkout`
- v3 candidate — embed `mermaid.min.js` in `sample.html` (offline-capable)
- v4 candidate — multiple sample themes (editorial / dashboard / minimal), user picks

## Project structure

```
impl-explain/
├── README.md / README.en.md    # Chinese / English README
├── SKILL.md                    # main skill file (prompt-only)
├── install.sh                  # one-line installer for all three agents
├── examples/
│   └── sample.html             # visual anchor (agent must read)
├── templates/
│   └── plan-template.md        # companion plan template + 4 anti-patterns
├── slash-wrappers/
│   ├── codex-prompt.md         # → ~/.codex/prompts/impl-explain.md
│   └── opencode-command.md     # → ~/.config/opencode/commands/impl-explain.md
├── docs/
│   ├── hero.png / preview.png  # README screenshots
│   └── plan/                   # this project's own plan
└── research/archive/           # 11 evaluation reports from v1 iteration
```

---

<div align="center">
<sub>v1 went through 7 rounds of multi-angle subagent evaluation; v2 lite simplifies after that loop revealed over-engineering. <br>
v1 evaluation reports archived in <a href="research/archive/">research/archive/</a>.</sub>
</div>
