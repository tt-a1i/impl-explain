#!/usr/bin/env python3
"""impl-explain HTML renderer.

输入 JSON（stdin 或 --input），按固定结构渲染单文件 HTML 实施报告到磁盘。
Python 3 stdlib only. 无 pip 依赖。Mermaid 走 CDN。

JSON schema 详见项目根目录 docs/plan/2026-05-11-implementation-plan.md 第 A.1 节。
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any


# ============================================================
# Schema validation
# ============================================================


class SchemaError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        msg = "schema 校验失败:\n  - " + "\n  - ".join(errors)
        super().__init__(msg)


# mermaid 启发式：首行需以关键字开头（允许 %%{init: ...}%% 前缀，含嵌套花括号）
_MERMAID_RE = re.compile(
    r"^\s*(?:%%\{[\s\S]*?\}%%\s*)*"  # 任意个 init 块前缀, 允许嵌套花括号
    r"\b(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram|"
    r"erDiagram|gantt|pie|journey|gitGraph|mindmap|timeline|"
    r"requirement|C4Context|C4Container)\b",
    re.IGNORECASE,
)


def _check_mermaid_syntax(diagram: str, field: str, errors: list[str]) -> None:
    if not _MERMAID_RE.match(diagram):
        errors.append(
            f"`{field}` 看起来不是 mermaid 语法（首行需以 flowchart / graph / sequenceDiagram 等开头）。"
            f"如果只是 ASCII 图，请省略该字段让对应 section 不出现。"
        )


def _check_kind(value: Any, *, field: str, kind: type | tuple[type, ...], errors: list[str]) -> bool:
    if value is None:
        errors.append(f"`{field}` 缺失")
        return False
    if not isinstance(value, kind):
        kind_name = kind.__name__ if isinstance(kind, type) else " | ".join(k.__name__ for k in kind)
        errors.append(f"`{field}` 类型错（期望 {kind_name}，实际 {type(value).__name__}）")
        return False
    return True


def _check_optional_kind(value: Any, *, field: str, kind: type | tuple[type, ...], errors: list[str]) -> bool:
    if value is None:
        return False
    return _check_kind(value, field=field, kind=kind, errors=errors)


def validate(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    if not isinstance(data, dict):
        raise SchemaError(["根对象必须是 JSON object"])

    # ----- meta -----
    if _check_kind(data.get("meta"), field="meta", kind=dict, errors=errors):
        meta = data["meta"]
        for key in ("title", "date", "plan_file"):
            _check_kind(meta.get(key), field=f"meta.{key}", kind=str, errors=errors)
        _check_optional_kind(meta.get("subtitle"), field="meta.subtitle", kind=str, errors=errors)
        _check_optional_kind(meta.get("git_range"), field="meta.git_range", kind=str, errors=errors)
        if _check_optional_kind(meta.get("commits"), field="meta.commits", kind=list, errors=errors):
            for i, c in enumerate(meta["commits"]):
                _check_kind(c, field=f"meta.commits[{i}]", kind=str, errors=errors)
        if _check_optional_kind(meta.get("metrics"), field="meta.metrics", kind=list, errors=errors):
            for i, m in enumerate(meta["metrics"]):
                if _check_kind(m, field=f"meta.metrics[{i}]", kind=dict, errors=errors):
                    _check_kind(m.get("label"), field=f"meta.metrics[{i}].label", kind=str, errors=errors)
                    _check_kind(m.get("value"), field=f"meta.metrics[{i}].value", kind=str, errors=errors)
                    _check_optional_kind(m.get("hint"), field=f"meta.metrics[{i}].hint", kind=str, errors=errors)

    # ----- tldr -----
    if _check_kind(data.get("tldr"), field="tldr", kind=dict, errors=errors):
        tldr = data["tldr"]
        for key in ("goal", "approach", "tradeoff"):
            _check_kind(tldr.get(key), field=f"tldr.{key}", kind=str, errors=errors)

    # ----- architecture_diagram -----
    arch = data.get("architecture_diagram")
    if arch is not None:
        if _check_kind(arch, field="architecture_diagram", kind=dict, errors=errors):
            _check_kind(arch.get("type"), field="architecture_diagram.type", kind=str, errors=errors)
            if _check_kind(arch.get("diagram"), field="architecture_diagram.diagram", kind=str, errors=errors):
                _check_mermaid_syntax(arch["diagram"], "architecture_diagram.diagram", errors)
            _check_optional_kind(arch.get("summary"), field="architecture_diagram.summary", kind=str, errors=errors)
            _check_optional_kind(arch.get("caption"), field="architecture_diagram.caption", kind=str, errors=errors)

    # ----- data_flow -----
    flow = data.get("data_flow")
    if flow is not None:
        if _check_kind(flow, field="data_flow", kind=dict, errors=errors):
            if _check_kind(flow.get("before"), field="data_flow.before", kind=str, errors=errors):
                _check_mermaid_syntax(flow["before"], "data_flow.before", errors)
            if _check_kind(flow.get("after"), field="data_flow.after", kind=str, errors=errors):
                _check_mermaid_syntax(flow["after"], "data_flow.after", errors)

    # ----- decisions (强制至少 1, warn if < 3) -----
    decisions = data.get("decisions") or []
    if _check_kind(decisions, field="decisions", kind=list, errors=errors):
        if len(decisions) == 0:
            errors.append(
                "`decisions` 为空——一份没有决策的实施报告意义不大；如果 plan 里真的没决策，"
                "先 grep commit body 找 'why' / '因为' / '考虑过' 关键词补全，或问用户口头补几条。"
            )
        for i, d in enumerate(decisions):
            if not _check_kind(d, field=f"decisions[{i}]", kind=dict, errors=errors):
                continue
            # title 兼容 question（旧字段名）
            title_field = "title" if "title" in d else "question"
            _check_kind(d.get(title_field), field=f"decisions[{i}].{title_field}", kind=str, errors=errors)
            _check_kind(d.get("chosen"), field=f"decisions[{i}].chosen", kind=str, errors=errors)
            _check_kind(d.get("rationale"), field=f"decisions[{i}].rationale", kind=str, errors=errors)
            _check_kind(d.get("status"), field=f"decisions[{i}].status", kind=str, errors=errors)
            if isinstance(d.get("status"), str) and d["status"] not in ("chosen", "deferred"):
                errors.append(
                    f"`decisions[{i}].status` 必须是 chosen 或 deferred（rejected 已废弃——"
                    f"如果决策本身被否决，多半应该放进 out_of_scope 而不是 decisions）"
                )
            if d.get("rejected") is not None:
                if _check_kind(d.get("rejected"), field=f"decisions[{i}].rejected", kind=list, errors=errors):
                    for j, r in enumerate(d["rejected"]):
                        _check_kind(r, field=f"decisions[{i}].rejected[{j}]", kind=str, errors=errors)
            _check_optional_kind(d.get("cost"), field=f"decisions[{i}].cost", kind=str, errors=errors)
            _check_optional_kind(d.get("question"), field=f"decisions[{i}].question", kind=str, errors=errors)

    # ----- risks (强制至少 1) -----
    risks = data.get("risks") or []
    if _check_kind(risks, field="risks", kind=list, errors=errors):
        if len(risks) == 0:
            errors.append(
                "`risks` 为空——'无风险'通常不真实，至少列 2-3 条；如果真的找不到，"
                "想想'多副本部署'、'依赖第三方'、'静默失败'这三类常见隐患。"
            )
        for i, r in enumerate(risks):
            if not _check_kind(r, field=f"risks[{i}]", kind=dict, errors=errors):
                continue
            _check_kind(r.get("description"), field=f"risks[{i}].description", kind=str, errors=errors)
            _check_kind(r.get("severity"), field=f"risks[{i}].severity", kind=str, errors=errors)
            if isinstance(r.get("severity"), str) and r["severity"] not in ("low", "medium", "high"):
                errors.append(
                    f"`risks[{i}].severity` 必须是 low / medium / high，实际 {r['severity']!r}"
                )
            # mitigation 三态优先；mitigated bool 兜底
            if "mitigation" in r:
                _check_kind(r.get("mitigation"), field=f"risks[{i}].mitigation", kind=str, errors=errors)
                if isinstance(r.get("mitigation"), str) and r["mitigation"] not in ("full", "partial", "none"):
                    errors.append(
                        f"`risks[{i}].mitigation` 必须是 full / partial / none，实际 {r['mitigation']!r}"
                    )
            elif "mitigated" in r:
                _check_kind(r.get("mitigated"), field=f"risks[{i}].mitigated", kind=bool, errors=errors)
            else:
                errors.append(
                    f"`risks[{i}]` 缺少 mitigation（推荐三态 full/partial/none）或 mitigated（bool，兜底）"
                )
            _check_optional_kind(r.get("note"), field=f"risks[{i}].note", kind=str, errors=errors)

    # ----- out_of_scope -----
    oos = data.get("out_of_scope") or []
    if _check_kind(oos, field="out_of_scope", kind=list, errors=errors):
        for i, s in enumerate(oos):
            _check_kind(s, field=f"out_of_scope[{i}]", kind=str, errors=errors)

    if errors:
        raise SchemaError(errors)
    return data


# ============================================================
# Helpers
# ============================================================


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def mermaid_text(s: str) -> str:
    """Escape mermaid source for safe insertion into a data attribute.

    Mermaid source comes from LLM-generated JSON, so any HTML-looking content
    (e.g. node labels containing ``<img src=x onerror=...>``) is a potential
    injection vector. We escape everything via ``html.escape`` and store the
    result in ``data-content`` on the container. A small JS shim then copies
    ``el.dataset.content`` to ``el.textContent`` (NOT innerHTML) before
    ``mermaid.initialize`` runs, so the mermaid library reads inert text.

    Combined with ``htmlLabels: false`` in the mermaid theme config, node
    labels render as SVG ``<text>`` elements with no HTML interpretation.
    """
    return html.escape(s, quote=True)


def _resolve_mitigation(r: dict[str, Any]) -> tuple[str, str]:
    """Returns (level, label). Level: full|partial|none."""
    if "mitigation" in r:
        level = r["mitigation"]
    elif r.get("mitigated") is True:
        level = "full"
    else:
        level = "none"
    label = {"full": "已缓解", "partial": "部分缓解", "none": "待观察"}[level]
    return level, label


def _auto_metrics(data: dict[str, Any]) -> list[dict[str, str]]:
    """如果 meta.metrics 缺失，自动从 decisions / risks 派生。"""
    decisions = data.get("decisions") or []
    risks = data.get("risks") or []
    high_risks = sum(1 for r in risks if r.get("severity") == "high")
    metrics = [
        {"label": "决策", "value": str(len(decisions))},
        {"label": "风险", "value": str(len(risks)), "hint": f"{high_risks} high" if high_risks else None},
    ]
    return metrics


# ============================================================
# CSS / JS
# ============================================================


CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg: #faf7f2;
  --bg-soft: #f5f0e7;
  --bg-card: #fdfaf3;
  --border: #e9e3d8;
  --border-strong: #d6cdba;
  --rule: #ede5d3;
  --text: #1f1c17;
  --text-soft: #4a443a;
  --text-muted: #8a8275;
  --text-faint: #b8b0a0;
  --accent: #b04a1f;
  --accent-soft: #fbeede;
  --chosen: #4a6a2c;
  --chosen-soft: #ecefd9;
  --rejected: #7a2f24;
  --rejected-soft: #f1ddd5;
  --deferred: #8a5a17;
  --deferred-soft: #f6ecd6;
  --sev-high: #7a2f24;
  --sev-medium: #8a5a17;
  --sev-low: #a89970;
  --mit-full: #4a6a2c;
  --mit-partial: #8a5a17;
  --mit-none: #b8b0a0;
}

* { box-sizing: border-box; }
html { background: var(--bg); scroll-behavior: smooth; }

body {
  margin: 0;
  padding: 0;
  background: var(--bg);
  color: var(--text);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 17px;
  line-height: 1.7;
  -webkit-font-smoothing: antialiased;
}

/* ===== Progress bar ===== */
.progress-bar {
  position: fixed;
  top: 0;
  left: 0;
  height: 2px;
  background: var(--accent);
  z-index: 200;
  width: 0%;
  transition: width 80ms linear;
}

/* ===== Sticky TOC ===== */
.toc {
  position: sticky;
  top: 0;
  background: rgba(250, 247, 242, 0.92);
  backdrop-filter: saturate(140%) blur(10px);
  -webkit-backdrop-filter: saturate(140%) blur(10px);
  border-bottom: 1px solid var(--rule);
  z-index: 50;
}
.toc-inner {
  max-width: 760px;
  margin: 0 auto;
  padding: 14px 32px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px 24px;
  font-family: 'JetBrains Mono', ui-monospace, Menlo, monospace;
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}
.toc a {
  color: var(--text-muted);
  text-decoration: none;
  padding: 2px 0;
  border-bottom: 1px solid transparent;
  transition: color 120ms, border-color 120ms;
}
.toc a:hover { color: var(--text-soft); }
.toc a.active { color: var(--accent); border-bottom-color: var(--accent); }

.page {
  max-width: 760px;
  margin: 0 auto;
  padding: 64px 32px 120px;
}

section { margin: 80px 0 0; scroll-margin-top: 96px; }

h2.section-title {
  font-family: 'Fraunces', Georgia, serif;
  font-weight: 500;
  font-size: 13px;
  letter-spacing: 0.26em;
  text-transform: uppercase;
  color: var(--text-muted);
  font-style: normal;
  margin: 0 0 32px;
  display: flex;
  align-items: center;
  gap: 24px;
}
h2.section-title::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--rule);
}

/* ===== Header / Hero ===== */
.eyebrow {
  display: inline-block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 28px;
}
.eyebrow .dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  background: var(--accent);
  border-radius: 50%;
  vertical-align: middle;
  margin: 0 12px 2px;
}

h1.report-title {
  font-family: 'Fraunces', 'Times New Roman', Georgia, serif;
  font-weight: 600;
  font-size: 64px;
  line-height: 1.05;
  letter-spacing: -0.025em;
  color: var(--text);
  margin: 0 0 24px;
}
@media (max-width: 600px) {
  h1.report-title { font-size: 44px; }
  .page { padding: 48px 22px 80px; }
}

.report-subtitle {
  font-family: 'Fraunces', Georgia, serif;
  font-weight: 400;
  font-style: italic;
  font-size: 26px;
  line-height: 1.4;
  color: var(--text-soft);
  margin: 0 0 40px;
  max-width: 520px;
}

/* hero metrics */
.hero-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 16px 48px;
  margin: 0 0 36px;
}
.hero-metric .label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 6px;
}
.hero-metric .value {
  font-family: 'Fraunces', Georgia, serif;
  font-size: 44px;
  font-weight: 600;
  line-height: 1;
  color: var(--text);
  letter-spacing: -0.015em;
}
.hero-metric .hint {
  display: inline-block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
  margin-left: 10px;
  vertical-align: baseline;
}

.report-meta {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.12em;
  color: var(--text-muted);
  padding-top: 32px;
  border-top: 1px solid var(--rule);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.report-meta .item { display: flex; align-items: baseline; gap: 12px; }
.report-meta .item .key { color: var(--text-faint); flex-shrink: 0; min-width: 56px; }
.report-meta .item .val { color: var(--text-soft); word-break: break-all; }
.report-meta .commits {
  margin: 4px 0 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.report-meta .commits .item .key { color: transparent; }
.report-meta .commits .item .val { color: var(--text-muted); }

/* ===== TL;DR ===== */
.tldr { display: grid; grid-template-columns: 1fr; gap: 28px; }
.tldr-block {
  display: grid;
  grid-template-columns: 112px 1fr;
  gap: 32px;
  align-items: baseline;
  padding-bottom: 24px;
  border-bottom: 1px dashed var(--rule);
}
.tldr-block:last-child { border-bottom: none; padding-bottom: 0; }
.tldr-block .label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--text-muted);
  padding-top: 4px;
}
.tldr-block .body {
  font-family: 'Fraunces', Georgia, serif;
  font-size: 22px;
  line-height: 1.5;
  color: var(--text);
  font-weight: 400;
}
@media (max-width: 600px) {
  .tldr-block { grid-template-columns: 1fr; gap: 8px; }
  .tldr-block .body { font-size: 19px; }
}

/* ===== Risk Snapshot (头部摘要, 放在 Risks section 顶部) ===== */
.risk-snapshot {
  margin: -8px 0 28px;
  padding: 20px 24px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 2px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 14px 24px;
}
.risk-highlight {
  margin: 0 0 36px;
  padding: 14px 20px;
  background: rgba(122, 47, 36, 0.06);
  border-left: 3px solid var(--sev-high);
  border-radius: 2px;
  font-size: 15px;
  line-height: 1.55;
  color: var(--text);
}
.risk-highlight .label {
  display: inline-block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--sev-high);
  font-weight: 600;
  margin-right: 14px;
}
.risk-highlight.mit {
  background: rgba(74, 106, 44, 0.06);
  border-left-color: var(--mit-full);
}
.risk-highlight.mit .label { color: var(--mit-full); }
.risk-highlight .mit-meta { color: var(--text-muted); font-size: 13px; }
.risk-highlight .hl-note {
  display: block;
  margin-top: 8px;
  font-family: 'Fraunces', Georgia, serif;
  font-style: italic;
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.55;
}

/* ===== TL;DR tail: inline risk count row ===== */
.tldr-risk-tail {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid var(--rule);
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}
.tldr-risk-tail .label { color: var(--text-faint); }
.tldr-risk-tail .count { color: var(--text); font-weight: 600; }
.tldr-risk-tail .sev-high { color: var(--sev-high); font-weight: 600; }
.tldr-risk-tail .sev-medium { color: var(--sev-medium); font-weight: 600; }
.tldr-risk-tail .anchor {
  margin-left: auto;
  color: var(--accent);
  text-decoration: none;
  border-bottom: 1px solid currentColor;
  padding-bottom: 1px;
}
.tldr-risk-tail .anchor:hover { color: var(--text); border-bottom-color: var(--text); }

/* ===== Hero commits 折叠 ===== */
.report-meta .commits {
  margin: 4px 0 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.report-meta .commits-collapsed { max-height: calc(3 * (1em + 6px)); overflow: hidden; position: relative; }
.report-meta .commits-collapsed.expanded { max-height: 600px; }
.report-meta .commits-toggle {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--accent);
  background: none;
  border: none;
  padding: 6px 0 0;
  cursor: pointer;
}
.report-meta .commits-toggle:hover { color: var(--text); }
.risk-snapshot .label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--text-muted);
}
.risk-snapshot .total {
  font-family: 'Fraunces', Georgia, serif;
  font-size: 24px;
  color: var(--text);
}
.risk-snapshot .total .num { font-weight: 500; }
.risk-snapshot .total .word { color: var(--text-muted); margin-left: 6px; font-size: 14px; font-style: normal; }
.risk-snapshot .pills { display: flex; gap: 8px; flex-wrap: wrap; }
.risk-snapshot .pill {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  padding: 4px 10px;
  border-radius: 2px;
  font-weight: 600;
}
.risk-snapshot .pill.high { background: rgba(122, 47, 36, 0.12); color: var(--sev-high); }
.risk-snapshot .pill.medium { background: rgba(138, 90, 23, 0.12); color: var(--sev-medium); }
.risk-snapshot .pill.low { background: rgba(168, 153, 112, 0.18); color: var(--sev-low); }
.risk-snapshot .pill .mit { opacity: 0.7; margin-left: 6px; }

/* ===== Diagram ===== */
.diagram-summary {
  font-family: 'Inter', sans-serif;
  font-style: normal;
  font-size: 16px;
  line-height: 1.65;
  color: var(--text-soft);
  margin: 0 0 28px;
}
.diagram-summary .summary-label {
  display: block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 8px;
}
.diagram-wrap {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 2px;
  padding: 40px 32px;
  overflow-x: auto;
  text-align: center;
}
.diagram-wrap .mermaid {
  display: inline-block;
  min-width: 100%;
  font-family: 'Inter', sans-serif;
}
.diagram-caption {
  margin: 16px 0 0;
  font-family: 'Fraunces', Georgia, serif;
  font-style: italic;
  font-size: 14px;
  color: var(--text-muted);
  text-align: center;
}

/* ===== Data flow ===== */
.flow-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 28px;
  align-items: stretch;
}
.flow-cell {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 2px;
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
}
.flow-cell .mermaid {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}
.flow-cell .mermaid svg {
  max-width: 100%;
  height: auto;
}
.flow-cell .flow-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 20px;
  display: block;
}
.flow-cell.before .flow-label { color: var(--accent); }
.flow-cell.after .flow-label { color: var(--chosen); }
@media (max-width: 700px) {
  .flow-grid { grid-template-columns: 1fr; gap: 20px; }
}

/* ===== Decisions ===== */
.decisions-meta {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin: -16px 0 32px;
}
.decisions { display: flex; flex-direction: column; gap: 72px; }
.decision {
  display: grid;
  grid-template-columns: 88px 1fr;
  gap: 32px;
  position: relative;
}
.decision .num {
  font-family: 'Fraunces', Georgia, serif;
  font-weight: 500;
  font-size: 56px;
  line-height: 1;
  color: var(--rule);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}
.decision.status-deferred .num { color: var(--deferred-soft); }
.decision.status-deferred .body { opacity: 0.86; }
.decision.status-deferred .title { color: var(--text-soft); }

.decision .body { padding-top: 4px; }
.decision .title {
  font-family: 'Fraunces', Georgia, serif;
  font-size: 27px;
  line-height: 1.3;
  color: var(--text);
  font-weight: 500;
  margin: 0 0 4px;
  letter-spacing: -0.01em;
}
.decision .question {
  font-family: 'Fraunces', Georgia, serif;
  font-style: italic;
  font-size: 15px;
  line-height: 1.4;
  color: var(--text-muted);
  margin: 0 0 16px;
}

.decision .chosen-line {
  display: inline-flex;
  align-items: baseline;
  gap: 14px;
  margin: 0 0 16px;
  padding: 10px 16px 10px 14px;
  background: var(--chosen-soft);
  border-left: 4px solid var(--chosen);
  border-radius: 0;
  color: var(--text);
  font-size: 15px;
  line-height: 1.45;
  max-width: 100%;
}
.decision .chosen-line .tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--chosen);
  font-weight: 600;
  flex-shrink: 0;
}
.decision.status-deferred .chosen-line {
  background: var(--deferred-soft);
  border-left-color: var(--deferred);
}
.decision.status-deferred .chosen-line .tag { color: var(--deferred); }

.decision .rationale {
  font-size: 16px;
  line-height: 1.7;
  color: var(--text-soft);
  margin: 4px 0 16px;
}

.decision .rejected-line {
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  color: var(--text-muted);
  margin: 0 0 12px;
  line-height: 1.55;
}
.decision .rejected-line .rl-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-faint);
  margin-right: 12px;
}
.decision .rejected-line .item { margin-right: 12px; }

.decision .cost {
  font-family: 'Fraunces', Georgia, serif;
  font-style: italic;
  font-size: 14px;
  line-height: 1.55;
  color: var(--text-muted);
  border-top: 1px solid var(--rule);
  padding-top: 12px;
  margin-top: 8px;
}
.decision .cost .cost-label {
  font-family: 'JetBrains Mono', monospace;
  font-style: normal;
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-faint);
  margin-right: 12px;
  padding-right: 12px;
  border-right: 1px solid var(--rule);
}

.decision::after {
  content: '';
  position: absolute;
  bottom: -36px;
  left: 88px;
  width: 80px;
  height: 1px;
  background: var(--rule);
}
.decision:last-child::after { display: none; }

@media (max-width: 600px) {
  .decision { grid-template-columns: 1fr; gap: 8px; }
  .decision .num { font-size: 40px; }
  .decision .title { font-size: 22px; }
  .decision::after { left: 0; }
}

/* ===== Risks ===== */
.risks-meta {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin: -16px 0 28px;
}
.risk-list { display: flex; flex-direction: column; gap: 0; }
.risk-row {
  display: grid;
  grid-template-columns: 76px 1fr 100px;
  gap: 24px;
  padding: 22px 0;
  border-bottom: 1px solid var(--rule);
  align-items: baseline;
}
.risk-row:last-child { border-bottom: none; }
.risk-row .sev {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-weight: 600;
  padding-top: 2px;
}
.risk-row.sev-high .sev { color: var(--sev-high); }
.risk-row.sev-medium .sev { color: var(--sev-medium); }
.risk-row.sev-low .sev { color: var(--sev-low); }
.risk-row .desc {
  font-size: 16px;
  line-height: 1.55;
  color: var(--text);
}
.risk-row .desc .note {
  display: block;
  margin-top: 6px;
  font-family: 'Fraunces', Georgia, serif;
  font-style: italic;
  font-size: 13px;
  color: var(--text-muted);
}
.risk-row .mit {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  white-space: nowrap;
  padding-top: 2px;
  text-align: right;
}
.risk-row .mit.full { color: var(--mit-full); }
.risk-row .mit.partial { color: var(--mit-partial); }
.risk-row .mit.none { color: var(--mit-none); }
@media (max-width: 600px) {
  .risk-row { grid-template-columns: 1fr; gap: 4px; }
  .risk-row .mit { text-align: left; }
}

/* ===== Out of scope ===== */
.oos-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.oos-list li {
  font-family: 'Fraunces', Georgia, serif;
  font-style: italic;
  font-size: 16px;
  color: var(--text-muted);
  line-height: 1.55;
  padding-left: 28px;
  position: relative;
}
.oos-list li::before {
  content: '—';
  position: absolute;
  left: 0;
  color: var(--text-faint);
  font-style: normal;
  font-family: 'Fraunces', Georgia, serif;
  font-size: 16px;
  top: 0;
}

/* ===== Footer ===== */
footer.report-footer {
  margin-top: 120px;
  padding-top: 32px;
  border-top: 1px solid var(--rule);
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-faint);
  text-align: center;
}
footer.report-footer .end-mark {
  display: inline-block;
  width: 6px;
  height: 6px;
  background: var(--accent);
  border-radius: 50%;
  margin: 0 14px 2px;
  vertical-align: middle;
}
"""


JS = r"""
// 安全前导：把 data-content 复制到 textContent 后再交给 mermaid 渲染。
// 见 scripts/render.py::mermaid_text 注释。
(function () {
  document.querySelectorAll('.mermaid[data-content]').forEach(function (el) {
    el.textContent = el.dataset.content;
    el.removeAttribute('data-content');
  });
})();

mermaid.initialize({
  startOnLoad: true,
  theme: 'base',
  themeVariables: {
    background: '#fdfaf3',
    primaryColor: '#fbeede',
    primaryTextColor: '#1f1c17',
    primaryBorderColor: '#b04a1f',
    lineColor: '#a89685',
    secondaryColor: '#ffffff',
    tertiaryColor: '#f5f0e7',
    fontFamily: 'Inter, -apple-system, sans-serif',
    fontSize: '14px',
    nodeBorder: '#d6cdba',
    clusterBkg: '#f5f0e7',
    clusterBorder: '#e9e3d8',
    edgeLabelBackground: '#fdfaf3',
    titleColor: '#1f1c17'
  },
  // htmlLabels:false 强制 mermaid 把 node label 渲染成 SVG <text>，
  // 屏蔽 LLM 生成 label 内 <img src=x onerror=...> 这类 HTML 注入面。
  // 配合 mermaid_text() 的 html.escape 形成双层防护。
  flowchart: { curve: 'basis', padding: 12, htmlLabels: false },
  sequence: { actorMargin: 60, messageMargin: 40 }
});

// Progress bar
(function () {
  var bar = document.querySelector('.progress-bar');
  if (!bar) return;
  function update() {
    var max = document.documentElement.scrollHeight - window.innerHeight;
    var pct = max > 0 ? (window.scrollY / max) * 100 : 0;
    bar.style.width = pct + '%';
  }
  window.addEventListener('scroll', update, { passive: true });
  window.addEventListener('resize', update);
  update();
})();

// TOC active section
(function () {
  var links = Array.prototype.slice.call(document.querySelectorAll('.toc a[href^="#"]'));
  if (!links.length) return;
  var sectionMap = {};
  links.forEach(function (a) {
    var id = a.getAttribute('href').slice(1);
    var el = document.getElementById(id);
    if (el) sectionMap[id] = a;
  });
  // 初始 active: 第一个 link (TL;DR)
  if (links[0]) links[0].classList.add('active');

  var observer = new IntersectionObserver(function (entries) {
    // 收集当前在可视区的所有 section，按 doc order 取第一个作为 active
    var visible = [];
    entries.forEach(function (e) {
      if (e.isIntersecting) visible.push(e.target);
    });
    if (!visible.length) return;
    // 取 boundingClientRect.top 最小（最先进入视野）的
    visible.sort(function (a, b) { return a.getBoundingClientRect().top - b.getBoundingClientRect().top; });
    var id = visible[0].id;
    links.forEach(function (a) { a.classList.remove('active'); });
    var link = sectionMap[id];
    if (link) link.classList.add('active');
  }, { rootMargin: '-15% 0px -70% 0px', threshold: 0 });
  Object.keys(sectionMap).forEach(function (id) {
    var el = document.getElementById(id);
    if (el) observer.observe(el);
  });
})();

// Commits 折叠展开
(function () {
  var toggle = document.querySelector('.commits-toggle');
  if (!toggle) return;
  var commits = document.querySelector('.commits-collapsed');
  if (!commits) return;
  toggle.addEventListener('click', function () {
    var expanded = commits.classList.toggle('expanded');
    toggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    var count = commits.getAttribute('data-commits-count');
    toggle.textContent = expanded ? '折叠 commits' : ('展开全部 ' + count + ' commits');
  });
})();
"""


# ============================================================
# Rendering
# ============================================================


def render_progress_bar() -> str:
    return '<div class="progress-bar"></div>'


def render_toc() -> str:
    return """
<nav class="toc" aria-label="目录">
  <div class="toc-inner">
    <a href="#tldr">TL;DR</a>
    <a href="#architecture">Architecture</a>
    <a href="#flow">Before / After</a>
    <a href="#decisions">Decisions</a>
    <a href="#risks">Risks</a>
    <a href="#oos">Out of Scope</a>
  </div>
</nav>
"""


def render_header(data: dict[str, Any]) -> str:
    meta = data["meta"]
    date = esc(meta["date"])
    title = esc(meta["title"])
    subtitle_html = ""
    if meta.get("subtitle"):
        subtitle_html = f'<p class="report-subtitle">{esc(meta["subtitle"])}</p>'

    # metrics
    metrics = meta.get("metrics") or _auto_metrics(data)
    metric_items = []
    for m in metrics:
        hint = f'<span class="hint">{esc(m["hint"])}</span>' if m.get("hint") else ""
        metric_items.append(f"""
    <div class="hero-metric">
      <div class="label">{esc(m["label"])}</div>
      <div class="value">{esc(m["value"])}{hint}</div>
    </div>""")
    metrics_html = ""
    if metric_items:
        metrics_html = f'<div class="hero-metrics">{"".join(metric_items)}</div>'

    # meta footer (plan path, commits, git range)
    meta_lines: list[str] = [
        f'<div class="item"><span class="key">plan</span><span class="val">{esc(meta["plan_file"])}</span></div>'
    ]
    if meta.get("commits"):
        commits = list(meta["commits"])
        commits_html_items = "\n".join(
            f'      <div class="item"><span class="key">{("commits" if i == 0 else "·")}</span><span class="val">{esc(c)}</span></div>'
            for i, c in enumerate(commits)
        )
        if len(commits) > 3:
            meta_lines.append(
                f'<div class="commits commits-collapsed" data-commits-count="{len(commits)}">\n{commits_html_items}\n    </div>'
                f'\n    <button class="commits-toggle" type="button" aria-expanded="false">展开全部 {len(commits)} commits</button>'
            )
        else:
            meta_lines.append(f'<div class="commits">\n{commits_html_items}\n    </div>')
    elif meta.get("git_range"):
        meta_lines.append(
            f'<div class="item"><span class="key">range</span><span class="val">{esc(meta["git_range"])}</span></div>'
        )
    meta_html = "\n    ".join(meta_lines)

    return f"""
<header class="report-header">
  <div class="eyebrow">Implementation Report<span class="dot"></span>{date}</div>
  <h1 class="report-title">{title}</h1>
  {subtitle_html}
  {metrics_html}
  <div class="report-meta">
    {meta_html}
  </div>
</header>
"""


def render_tldr(tldr: dict[str, str], risks: list[dict[str, Any]] | None = None) -> str:
    tail_html = ""
    if risks:
        total = len(risks)
        high = sum(1 for r in risks if r.get("severity") == "high")
        high_unmit = sum(
            1 for r in risks
            if r.get("severity") == "high" and _resolve_mitigation(r)[0] != "full"
        )
        med = sum(1 for r in risks if r.get("severity") == "medium")

        parts = [f'<span class="label">风险预告</span>',
                 f'<span class="count">{total} risks</span>']
        if high:
            high_text = f"{high} high"
            if high_unmit == 0 and high > 0:
                high_text += " (已缓解)"
            elif high_unmit > 0:
                high_text += f" ({high_unmit} unmit)"
            parts.append(f'<span class="sev-high">· {high_text}</span>')
        if med:
            parts.append(f'<span class="sev-medium">· {med} medium</span>')
        parts.append('<a class="anchor" href="#risks">看详情 →</a>')

        tail_html = '\n  <div class="tldr-risk-tail">' + "".join(parts) + '</div>'

    return f"""
<section id="tldr" data-toc>
  <h2 class="section-title">TL;DR</h2>
  <div class="tldr">
    <div class="tldr-block">
      <div class="label">做什么</div>
      <div class="body">{esc(tldr["goal"])}</div>
    </div>
    <div class="tldr-block">
      <div class="label">怎么做</div>
      <div class="body">{esc(tldr["approach"])}</div>
    </div>
    <div class="tldr-block">
      <div class="label">代价</div>
      <div class="body">{esc(tldr["tradeoff"])}</div>
    </div>
  </div>{tail_html}
</section>
"""


def render_risk_snapshot(risks: list[dict[str, Any]]) -> str:
    """Snapshot bar + 最高 severity 风险一句话 highlight. 现在嵌入 Risks section 顶部。"""
    if not risks:
        return ""
    total = len(risks)
    by_sev: dict[str, list[dict[str, Any]]] = {"high": [], "medium": [], "low": []}
    for r in risks:
        by_sev.setdefault(r.get("severity", "low"), []).append(r)
    pills_html = ""
    for sev in ("high", "medium", "low"):
        items = by_sev.get(sev, [])
        if not items:
            continue
        mitigated = sum(1 for r in items if _resolve_mitigation(r)[0] in ("full", "partial"))
        if mitigated == len(items):
            mit_text = ' <span class="mit">(all mit)</span>'
        elif mitigated > 0:
            mit_text = f' <span class="mit">({mitigated}/{len(items)} mit)</span>'
        else:
            mit_text = ' <span class="mit">(0 mit)</span>'
        pills_html += f'<span class="pill {sev}">{len(items)} {sev}{mit_text}</span>'

    snapshot = f"""
<aside class="risk-snapshot" aria-label="风险概览">
  <span class="label">概览</span>
  <span class="total"><span class="num">{total}</span><span class="word">risks</span></span>
  <span class="pills">{pills_html}</span>
</aside>
"""

    # 选最高优先级的一条风险做 inline highlight。
    # 优先：高 severity 未缓解 > 高 severity full > 中 severity 未缓解 > ...
    top: dict[str, Any] | None = None
    for sev in ("high", "medium", "low"):
        if not by_sev.get(sev):
            continue
        unmit = [r for r in by_sev[sev] if _resolve_mitigation(r)[0] != "full"]
        if unmit:
            top = unmit[0]
            break
        # 同 severity 全 full mitigated 时, 高 severity 才考虑展示
        if sev == "high":
            top = by_sev[sev][0]
            break
    highlight_html = ""
    if top is not None:
        mit_level, mit_label = _resolve_mitigation(top)
        cls = "mit" if mit_level == "full" else ""
        prefix = "Top risk" if mit_level != "full" else "Top risk · 已缓解"
        # 用 description 直白；note（如有）作为 secondary 小字，避免技术细节抢主线
        body_text = top["description"]
        note_html = (
            f' <span class="hl-note">{esc(top["note"])}</span>'
            if top.get("note") else ""
        )
        highlight_html = f"""
<p class="risk-highlight {cls}">
  <span class="label">{prefix}</span>{esc(body_text)} <span class="mit-meta">— {esc(mit_label)}</span>{note_html}
</p>
"""

    return snapshot + highlight_html


def render_architecture(arch: dict[str, str] | None) -> str:
    if not arch:
        return ""
    summary_html = ""
    if arch.get("summary"):
        summary_html = (
            f'<p class="diagram-summary">'
            f'<span class="summary-label">叙述</span>{esc(arch["summary"])}'
            f"</p>"
        )
    caption = arch.get("caption", "")
    caption_html = f'<p class="diagram-caption">{esc(caption)}</p>' if caption else ""
    return f"""
<section id="architecture" data-toc>
  <h2 class="section-title">Architecture</h2>
  {summary_html}
  <div class="diagram-wrap">
    <div class="mermaid" data-content="{mermaid_text(arch["diagram"])}"></div>
  </div>
  {caption_html}
</section>
"""


def render_data_flow(flow: dict[str, str] | None) -> str:
    if not flow:
        return ""
    return f"""
<section id="flow" data-toc>
  <h2 class="section-title">Before / After</h2>
  <div class="flow-grid">
    <div class="flow-cell before">
      <span class="flow-label">Before</span>
      <div class="mermaid" data-content="{mermaid_text(flow["before"])}"></div>
    </div>
    <div class="flow-cell after">
      <span class="flow-label">After</span>
      <div class="mermaid" data-content="{mermaid_text(flow["after"])}"></div>
    </div>
  </div>
</section>
"""


def render_decisions(decisions: list[dict[str, Any]]) -> str:
    if not decisions:
        return ""
    chosen_count = sum(1 for d in decisions if d.get("status") == "chosen")
    deferred_count = sum(1 for d in decisions if d.get("status") == "deferred")
    meta_parts = [f"{len(decisions)} decisions"]
    if chosen_count:
        meta_parts.append(f"{chosen_count} chosen")
    if deferred_count:
        meta_parts.append(f"{deferred_count} deferred")
    meta_line = " · ".join(meta_parts)

    cards: list[str] = []
    for i, d in enumerate(decisions, 1):
        status = d["status"]
        status_label = {"chosen": "采用", "deferred": "推迟"}[status]
        title = d.get("title") or d.get("question", "")
        # question 字段在渲染中不再显示（IA 评估认定为冗余）；schema 中仍可存储

        rejected_html = ""
        if d.get("rejected"):
            items = " · ".join(f'<span class="item">{esc(r)}</span>' for r in d["rejected"])
            rejected_html = f'<p class="rejected-line"><span class="rl-label">放弃</span>{items}</p>'

        cost_html = ""
        if d.get("cost"):
            cost_html = f'<p class="cost"><span class="cost-label">代价</span>{esc(d["cost"])}</p>'

        num = f"{i:02d}"
        cards.append(f"""
<article class="decision status-{status}">
  <div class="num">{num}</div>
  <div class="body">
    <h3 class="title">{esc(title)}</h3>
    <div class="chosen-line">
      <span class="tag">{status_label}</span>
      <span class="text">{esc(d["chosen"])}</span>
    </div>
    <p class="rationale">{esc(d["rationale"])}</p>
    {rejected_html}
    {cost_html}
  </div>
</article>""")
    body = "".join(cards)
    return f"""
<section id="decisions" data-toc>
  <h2 class="section-title">Decisions</h2>
  <div class="decisions-meta">{meta_line}</div>
  <div class="decisions">{body}
  </div>
</section>
"""


def render_risks(risks: list[dict[str, Any]]) -> str:
    if not risks:
        return ""
    snapshot_html = render_risk_snapshot(risks)
    rows: list[str] = []
    for r in risks:
        note_html = f'<span class="note">{esc(r["note"])}</span>' if r.get("note") else ""
        mit_level, mit_label = _resolve_mitigation(r)
        rows.append(f"""
    <div class="risk-row sev-{r["severity"]}">
      <div class="sev">{esc(r["severity"])}</div>
      <div class="desc">{esc(r["description"])}{note_html}</div>
      <div class="mit {mit_level}">{mit_label}</div>
    </div>""")
    body = "".join(rows)
    return f"""
<section id="risks" data-toc>
  <h2 class="section-title">Risks</h2>
  {snapshot_html}
  <div class="risk-list">{body}
  </div>
</section>
"""


def render_out_of_scope(out_of_scope: list[str]) -> str:
    if not out_of_scope:
        return ""
    items = "\n".join(f"    <li>{esc(s)}</li>" for s in out_of_scope)
    return f"""
<section id="oos">
  <h2 class="section-title">Out of Scope</h2>
  <ul class="oos-list">
{items}
  </ul>
</section>
"""


def render_footer() -> str:
    return """
<footer class="report-footer">
  Generated by impl-explain<span class="end-mark"></span>End of report
</footer>
"""


def render_html(data: dict[str, Any]) -> str:
    meta = data["meta"]
    title = esc(meta["title"])
    body_html = (
        render_progress_bar()
        + render_toc()
        + '<div class="page">'
        + render_header(data)
        + render_tldr(data["tldr"], data.get("risks", []))
        + render_architecture(data.get("architecture_diagram"))
        + render_data_flow(data.get("data_flow"))
        + render_decisions(data.get("decisions", []))
        + render_risks(data.get("risks", []))
        + render_out_of_scope(data.get("out_of_scope", []))
        + render_footer()
        + "</div>"
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} · Implementation Report</title>
  <script src="https://unpkg.com/mermaid@11/dist/mermaid.min.js"></script>
  <style>{CSS}</style>
</head>
<body>
{body_html}
  <script>{JS}</script>
</body>
</html>
"""


# ============================================================
# CLI
# ============================================================


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="render.py",
        description="把 implementation summary JSON 渲染成单文件 HTML 实施报告",
    )
    parser.add_argument("--input", "-i", type=str, default="-", help="输入 JSON 路径（默认 stdin）")
    parser.add_argument(
        "--output", "-o", type=str, default="impl-explain.html", help="输出 HTML 路径（默认 ./impl-explain.html）"
    )
    args = parser.parse_args(argv)

    if args.input == "-":
        raw = sys.stdin.read()
    else:
        path = Path(args.input)
        if not path.exists():
            print(f"error: 输入文件不存在: {path}", file=sys.stderr)
            return 2
        raw = path.read_text(encoding="utf-8")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"error: 输入不是合法 JSON: {exc}", file=sys.stderr)
        return 2

    try:
        validated = validate(data)
    except SchemaError as exc:
        for line in str(exc).split("\n"):
            print(line, file=sys.stderr)
        return 2

    html_text = render_html(validated)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # 原子写入：先写临时文件，再 os.replace 替换目标，避免中断 / 磁盘满 / 异常时
    # 留下半成品 HTML 让浏览器读到坏内容。
    import os
    import tempfile

    fd, tmp_path = tempfile.mkstemp(
        prefix=out_path.name + ".",
        suffix=".tmp",
        dir=str(out_path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html_text)
        os.replace(tmp_path, out_path)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise

    print(f"✓ 报告已生成: {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
