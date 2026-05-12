"""Unit tests for scripts/render.py.

Stdlib only (unittest)，no pytest dependency。覆盖：
- validate() schema 校验各错误路径
- mermaid_text() 注入加固
- _resolve_mitigation() 三态判定（含旧 mitigated bool 兼容）
- _auto_metrics() 自动派生
- render_html() 端到端 happy path
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

# 让 tests/ 能 import scripts/render.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import render  # noqa: E402


def _minimal_valid_data() -> dict:
    """最小可通过 schema 的输入，作为各负面用例的基底。"""
    return {
        "meta": {
            "title": "Test",
            "date": "2026-05-12",
            "plan_file": "docs/plans/test.md",
        },
        "tldr": {"goal": "g", "approach": "a", "tradeoff": "t"},
        "decisions": [
            {
                "title": "D1",
                "chosen": "X",
                "rationale": "R",
                "status": "chosen",
            }
        ],
        "risks": [
            {
                "description": "r1",
                "severity": "low",
                "mitigation": "full",
            }
        ],
    }


class ValidateTests(unittest.TestCase):
    def test_minimal_valid_passes(self) -> None:
        data = _minimal_valid_data()
        render.validate(data)  # should not raise

    def test_root_not_dict_raises(self) -> None:
        with self.assertRaises(render.SchemaError):
            render.validate("not a dict")  # type: ignore[arg-type]

    def test_missing_meta_raises(self) -> None:
        data = _minimal_valid_data()
        del data["meta"]
        with self.assertRaises(render.SchemaError) as cm:
            render.validate(data)
        self.assertIn("meta", str(cm.exception))

    def test_meta_title_must_be_string(self) -> None:
        data = _minimal_valid_data()
        data["meta"]["title"] = 123
        with self.assertRaises(render.SchemaError) as cm:
            render.validate(data)
        self.assertIn("meta.title", str(cm.exception))

    def test_empty_decisions_raises(self) -> None:
        data = _minimal_valid_data()
        data["decisions"] = []
        with self.assertRaises(render.SchemaError) as cm:
            render.validate(data)
        self.assertIn("decisions", str(cm.exception))

    def test_empty_risks_raises(self) -> None:
        data = _minimal_valid_data()
        data["risks"] = []
        with self.assertRaises(render.SchemaError) as cm:
            render.validate(data)
        self.assertIn("risks", str(cm.exception))

    def test_decisions_status_rejected_blocked(self) -> None:
        data = _minimal_valid_data()
        data["decisions"][0]["status"] = "rejected"
        with self.assertRaises(render.SchemaError) as cm:
            render.validate(data)
        self.assertIn("status", str(cm.exception))

    def test_decisions_status_chosen_ok(self) -> None:
        data = _minimal_valid_data()
        data["decisions"][0]["status"] = "chosen"
        render.validate(data)

    def test_decisions_status_deferred_ok(self) -> None:
        data = _minimal_valid_data()
        data["decisions"][0]["status"] = "deferred"
        render.validate(data)

    def test_risks_severity_invalid_blocked(self) -> None:
        data = _minimal_valid_data()
        data["risks"][0]["severity"] = "critical"  # 不在枚举
        with self.assertRaises(render.SchemaError) as cm:
            render.validate(data)
        self.assertIn("severity", str(cm.exception))

    def test_risks_mitigation_three_state(self) -> None:
        data = _minimal_valid_data()
        for level in ("full", "partial", "none"):
            data["risks"][0]["mitigation"] = level
            render.validate(data)

    def test_risks_mitigation_invalid_blocked(self) -> None:
        data = _minimal_valid_data()
        data["risks"][0]["mitigation"] = "yes"
        with self.assertRaises(render.SchemaError) as cm:
            render.validate(data)
        self.assertIn("mitigation", str(cm.exception))

    def test_risks_mitigated_bool_legacy_ok(self) -> None:
        """旧字段 mitigated: bool 仍兼容。"""
        data = _minimal_valid_data()
        del data["risks"][0]["mitigation"]
        data["risks"][0]["mitigated"] = True
        render.validate(data)

    def test_risks_neither_mitigation_nor_mitigated_blocked(self) -> None:
        data = _minimal_valid_data()
        del data["risks"][0]["mitigation"]
        with self.assertRaises(render.SchemaError) as cm:
            render.validate(data)
        self.assertIn("mitigation", str(cm.exception))

    def test_mermaid_must_start_with_keyword(self) -> None:
        data = _minimal_valid_data()
        data["architecture_diagram"] = {
            "type": "mermaid",
            "diagram": "ASCII art here\n  A -> B",  # 非 mermaid 关键字
        }
        with self.assertRaises(render.SchemaError) as cm:
            render.validate(data)
        self.assertIn("mermaid", str(cm.exception).lower())

    def test_mermaid_with_init_block_ok(self) -> None:
        """允许 mermaid %%{init: ...}%% 前导。"""
        data = _minimal_valid_data()
        data["architecture_diagram"] = {
            "type": "mermaid",
            "diagram": "%%{init: {'theme': 'base'}}%%\nflowchart LR\n  A --> B",
        }
        render.validate(data)

    def test_aggregated_errors(self) -> None:
        """多处错误一次性返回，避免 agent 修一处跑一次的循环。"""
        data = _minimal_valid_data()
        data["meta"]["title"] = 123
        data["decisions"][0]["status"] = "weird"
        data["risks"][0]["severity"] = "extreme"
        with self.assertRaises(render.SchemaError) as cm:
            render.validate(data)
        message = str(cm.exception)
        # 三处错误都应出现
        self.assertIn("title", message)
        self.assertIn("status", message)
        self.assertIn("severity", message)


class MermaidTextTests(unittest.TestCase):
    def test_normal_mermaid_escaped_safely(self) -> None:
        """普通 mermaid 源被完整 html-escape，等待 JS shim 解码。"""
        src = "flowchart LR\n  A --> B"
        out = render.mermaid_text(src)
        self.assertIn("&gt;", out)
        # 原始 < > 不应保留为可执行 HTML
        self.assertNotIn("<", out.replace("&lt;", "").replace("&gt;", ""))

    def test_script_tag_in_label_escaped(self) -> None:
        """LLM 生成 mermaid 含 <script> 不能裸传 HTML。"""
        src = 'A["<script>alert(1)</script>"]'
        out = render.mermaid_text(src)
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)

    def test_img_onerror_escaped(self) -> None:
        src = 'A["<img src=x onerror=alert(1)>"]'
        out = render.mermaid_text(src)
        self.assertNotIn("<img", out)
        self.assertIn("&lt;img", out)

    def test_quote_chars_escaped(self) -> None:
        """data-content attribute 边界字符要 escape，否则破出属性。"""
        src = 'A["She said \\"hi\\""]'
        out = render.mermaid_text(src)
        self.assertNotIn('"', out)
        self.assertIn("&quot;", out)


class MitigationResolveTests(unittest.TestCase):
    def test_mitigation_full(self) -> None:
        r = {"mitigation": "full"}
        level, label = render._resolve_mitigation(r)
        self.assertEqual(level, "full")
        self.assertEqual(label, "已缓解")

    def test_mitigation_partial(self) -> None:
        r = {"mitigation": "partial"}
        level, label = render._resolve_mitigation(r)
        self.assertEqual(level, "partial")
        self.assertEqual(label, "部分缓解")

    def test_mitigation_none(self) -> None:
        r = {"mitigation": "none"}
        level, label = render._resolve_mitigation(r)
        self.assertEqual(level, "none")
        self.assertEqual(label, "待观察")

    def test_legacy_mitigated_true(self) -> None:
        r = {"mitigated": True}
        level, _ = render._resolve_mitigation(r)
        self.assertEqual(level, "full")

    def test_legacy_mitigated_false(self) -> None:
        r = {"mitigated": False}
        level, _ = render._resolve_mitigation(r)
        self.assertEqual(level, "none")

    def test_mitigation_overrides_legacy(self) -> None:
        """mitigation 字段优先于 mitigated bool。"""
        r = {"mitigation": "partial", "mitigated": True}
        level, _ = render._resolve_mitigation(r)
        self.assertEqual(level, "partial")


class AutoMetricsTests(unittest.TestCase):
    def test_auto_metrics_basic(self) -> None:
        data = _minimal_valid_data()
        metrics = render._auto_metrics(data)
        # 至少派生 决策 + 风险
        labels = [m["label"] for m in metrics]
        self.assertIn("决策", labels)
        self.assertIn("风险", labels)

    def test_auto_metrics_high_risk_hint(self) -> None:
        data = _minimal_valid_data()
        data["risks"].append(
            {"description": "h", "severity": "high", "mitigation": "none"}
        )
        metrics = render._auto_metrics(data)
        risk_metric = next(m for m in metrics if m["label"] == "风险")
        self.assertIsNotNone(risk_metric.get("hint"))
        self.assertIn("high", risk_metric["hint"])


class RenderHtmlTests(unittest.TestCase):
    def test_end_to_end_minimal(self) -> None:
        data = _minimal_valid_data()
        html_out = render.render_html(data)
        self.assertIn("<!DOCTYPE html>", html_out)
        self.assertIn(data["meta"]["title"], html_out)
        self.assertIn("D1", html_out)
        # mermaid 库引用必须在 head
        self.assertIn("mermaid", html_out)

    def test_demo_fixture_renders(self) -> None:
        """examples 里的 demo JSON 必须能渲染（防止 schema 与 demo 漂移）。"""
        fixture = PROJECT_ROOT / "examples" / "unified-source-sync-manager.input.json"
        data = json.loads(fixture.read_text(encoding="utf-8"))
        render.validate(data)
        html_out = render.render_html(data)
        self.assertIn(data["meta"]["title"], html_out)
        # 每个 decision 的 title 都应出现
        for d in data["decisions"]:
            self.assertIn(d["title"], html_out)


if __name__ == "__main__":
    unittest.main()
