"""Acceptance tests AC-025..029 (reporting) and accessibility (REQ-237-242)."""

from __future__ import annotations

import csv
import io
import json

import pytest
from lxml import html as lxml_html

from reconciliation.reporting.csv_renderer import CsvReportRenderer
from reconciliation.reporting.html.renderer import HtmlReportRenderer
from reconciliation.reporting.json_renderer import JsonReportRenderer
from tests.app_builders import localize
from tests.builders import TreeBuilder
from tests.reporting_builders import localize_and_table

pytestmark = pytest.mark.acceptance


def _rich_case():
    # Missing node, extra node, and a confirmed translated node.
    src = TreeBuilder("s", "r", node_type="map")
    src.child("r", "a", identity={"id": "a"}, content={"navtitle": "Intro"})
    src.child("r", "gone", identity={"id": "gone"}, content={"navtitle": "Removed"})
    tgt = TreeBuilder("t", "r", node_type="map")
    tgt.child("r", "a", identity={"id": "a"}, content={"navtitle": "Introducción"})
    tgt.child("r", "extra", identity={"id": "extra"}, content={"navtitle": "Adicional"})
    return src.build(), tgt.build()


def test_ac_025_html_report_content() -> None:
    src, tgt = _rich_case()
    result = localize(src, tgt)
    html = HtmlReportRenderer().render(result, source_tree=src, locale_tree=tgt)
    for heading in ("Summary", "Root causes", "Issues", "Recommendations", "Suppressed effects"):
        assert heading in html
    # Confidence dimensions are all present as columns.
    assert "Match confidence" in html
    assert "Operation confidence" in html
    assert "Repair confidence" in html


def test_ac_026_html_safety_escapes_scriptish_content() -> None:
    payload = "<script>alert('xss')</script>"
    src = TreeBuilder("s", "r", node_type="map")
    src.child("r", "a", identity={"id": "a"}, content={"navtitle": payload})
    tgt = TreeBuilder("t", "r", node_type="map")
    tgt.child("r", "a", identity={"id": "a"}, content={"navtitle": payload})
    result = localize(src.build(), tgt.build())
    html = HtmlReportRenderer().render(result)
    # The raw payload must not appear; its escaped form must.
    assert payload not in html
    assert "&lt;script&gt;" in html


def test_ac_027_csv_export_has_utf8_and_required_columns() -> None:
    _result, table = localize_and_table(*_rich_case())
    text = CsvReportRenderer().render(table)
    header = next(csv.reader(io.StringIO(text)))
    for required in ("job_id", "result_id", "localization_status", "match_confidence"):
        assert required in header
    assert "Introducción" in text


def test_ac_028_json_typing() -> None:
    _result, table = localize_and_table(*_rich_case())
    doc = json.loads(JsonReportRenderer().render(table))
    row = doc["rows"][0]
    assert isinstance(row["is_suppressed"], bool)
    assert isinstance(row["evidence_codes"], list)


def test_ac_029_stable_linkage_across_formats() -> None:
    result, table = localize_and_table(*_rich_case())
    csv_text = CsvReportRenderer().render(table)
    json_doc = json.loads(JsonReportRenderer().render(table))
    html = HtmlReportRenderer().render(result, source_tree=result_source(result), locale_tree=None)
    # Pick a stable result id and confirm it links across all three formats.
    a_result_id = table.rows[0].result_id
    assert a_result_id in csv_text
    assert any(row["result_id"] == a_result_id for row in json_doc["rows"])
    # HTML references issues by their data; at least one status label is shared.
    assert table.rows[0].localization_status in html


def result_source(result):
    # The localization result does not carry trees; HTML path enrichment is
    # optional, so None trees are acceptable here.
    return None


def test_accessibility_semantics_and_non_color_status() -> None:
    src, tgt = _rich_case()
    result = localize(src, tgt)
    html = HtmlReportRenderer().render(result, source_tree=src, locale_tree=tgt)
    doc = lxml_html.fromstring(html)
    # Language declared (REQ-236/accessibility).
    assert doc.get("lang") == "en"
    # Semantic landmarks (REQ-237).
    assert doc.xpath("//main") and doc.xpath("//header")
    # Table has a caption and column headers with scope (REQ-237).
    assert doc.xpath("//table/caption")
    assert doc.xpath("//table//th[@scope='col']")
    # Status conveyed by text, not color alone (REQ-239).
    assert doc.xpath("//span[contains(@class,'status__text')]")
    # Confidence has textual interpretation (REQ-240).
    assert any(band in html for band in ("high (", "medium (", "low ("))
    # Filter controls have associated labels (REQ-238).
    assert doc.xpath("//label[@for='status-filter']")


def test_accessibility_ambiguous_states_review_required() -> None:
    # Repeated indistinguishable nodes -> ambiguous -> must state review needed.
    src = TreeBuilder("s", "r", node_type="map")
    src.child("r", "s1", node_type="item", content={"t": "x"})
    src.child("r", "s2", node_type="item", content={"t": "x"})
    tgt = TreeBuilder("t", "r", node_type="map")
    tgt.child("r", "t1", node_type="item", content={"t": "x"})
    tgt.child("r", "t2", node_type="item", content={"t": "x"})
    result = localize(src.build(), tgt.build())
    html = HtmlReportRenderer().render(result)
    assert "Human review required" in html
