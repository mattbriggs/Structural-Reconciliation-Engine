"""Unit tests for the JSON/CSV/summary renderers and row building."""

from __future__ import annotations

import csv
import io
import json

from reconciliation.reporting.contracts import ReportOptions, ReportTable
from reconciliation.reporting.csv_renderer import CsvReportRenderer
from reconciliation.reporting.json_renderer import JsonReportRenderer
from reconciliation.reporting.summary_renderer import SummaryRenderer
from tests.builders import TreeBuilder
from tests.reporting_builders import localize_and_table


def _missing_case():
    src = TreeBuilder("s", "r", node_type="map")
    src.child("r", "a", identity={"id": "a"}).child("r", "b", identity={"id": "b"})
    tgt = TreeBuilder("t", "r", node_type="map")
    tgt.child("r", "a", identity={"id": "a"})
    return src.build(), tgt.build()


def test_rows_link_to_job_and_have_stable_ids() -> None:
    _result, table = localize_and_table(*_missing_case())
    assert all(row.job_id == "job-test" for row in table.rows)
    assert all(row.result_id for row in table.rows)
    assert table.schema_version == "report-v1"


def test_suppressed_rows_included_and_excludable() -> None:
    src = TreeBuilder("s", "r", node_type="map")
    src.child("r", "a", identity={"id": "a"}).child("r", "b", identity={"id": "b"})
    tgt = TreeBuilder("t", "r", node_type="map")
    tgt.child("r", "a", identity={"id": "a"}).child("r", "x", identity={"id": "x"}).child(
        "r", "b", identity={"id": "b"}
    )
    _r, with_suppressed = localize_and_table(src.build(), tgt.build())
    _r2, without = localize_and_table(
        src.build(), tgt.build(), options=ReportOptions(include_suppressed=False)
    )
    assert any(row.is_suppressed for row in with_suppressed.rows)
    assert not any(row.is_suppressed for row in without.rows)


def test_redaction_hides_labels() -> None:
    src = TreeBuilder("s", "r", node_type="map")
    src.child("r", "a", identity={"id": "a"}, content={"navtitle": "Secret Title"})
    tgt = TreeBuilder("t", "r", node_type="map")
    tgt.child("r", "a", identity={"id": "a"}, content={"navtitle": "Secret Title"})
    _r, table = localize_and_table(
        src.build(), tgt.build(), options=ReportOptions(redact_content=True)
    )
    for row in table.rows:
        assert row.source_label in (None, "[redacted]")


def test_csv_contains_all_columns_and_is_utf8() -> None:
    src = TreeBuilder("s", "r", node_type="map")
    src.child("r", "a", identity={"id": "a"}, content={"navtitle": "Café — Introducción"})
    tgt = TreeBuilder("t", "r", node_type="map")
    tgt.child("r", "a", identity={"id": "a"}, content={"navtitle": "Café — Introducción"})
    _r, table = localize_and_table(src.build(), tgt.build())
    text = CsvReportRenderer().render(table)
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    assert header == list(ReportTable.columns())
    assert "Café — Introducción" in text  # UTF-8 preserved (REQ-154)
    assert text.encode("utf-8")  # round-trips as UTF-8


def test_json_preserves_types() -> None:
    _result, table = localize_and_table(*_missing_case())
    doc = json.loads(JsonReportRenderer().render(table))
    assert doc["schema_version"] == "report-v1"
    for row in doc["rows"]:
        assert isinstance(row["is_suppressed"], bool)
        assert isinstance(row["evidence_codes"], list)
        if row["match_confidence"] is not None:
            assert isinstance(row["match_confidence"], (int, float))


def test_json_render_full_envelope() -> None:
    result, table = localize_and_table(*_missing_case())
    doc = json.loads(JsonReportRenderer().render_full(result, table))
    assert doc["localization_contract_version"] == "localization-result-v1"
    for key in ("versions", "summary", "issues", "recommendations", "suppressed_effects", "rows"):
        assert key in doc
    assert isinstance(doc["issues"], list)
    assert doc["versions"]["engine_version"]


def test_summary_render_has_counts_and_rates() -> None:
    result, _table = localize_and_table(*_missing_case())
    doc = json.loads(SummaryRenderer().render(result))
    assert "status_counts" in doc
    assert "rates" in doc
    assert doc["node_counts"]["missing"] >= 1
