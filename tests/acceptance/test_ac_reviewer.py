"""Acceptance test AC-030 (reviewer decision preservation)."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime

import pytest

from reconciliation.application.contracts.reviews import DecisionType, ReviewerDecisionCommand
from reconciliation.application.services.reviewer_decisions import ReviewerDecisionService
from reconciliation.reporting.csv_renderer import CsvReportRenderer
from reconciliation.reporting.rows import build_report_table
from tests.app_builders import localize
from tests.builders import TreeBuilder

pytestmark = pytest.mark.acceptance


def test_ac_030_reviewer_override_preserves_original_conclusion() -> None:
    src = TreeBuilder("s", "r", node_type="map")
    src.child("r", "a", identity={"id": "a"}).child("r", "b", identity={"id": "b"})
    tgt = TreeBuilder("t", "r", node_type="map")
    tgt.child("r", "a", identity={"id": "a"})
    result = localize(src.build(), tgt.build(), job_id="job-30")

    issue = next(i for i in result.issues if i.localization_status.value == "MISSING_IN_LOCALE")
    service = ReviewerDecisionService(
        clock=lambda: datetime(2026, 1, 1, tzinfo=UTC), id_factory=lambda: "decision-1"
    )
    decision = service.record(
        ReviewerDecisionCommand(
            job_id="job-30",
            issue_id=issue.issue_id,
            decision=DecisionType.OVERRIDE,
            overridden_status="EXEMPT_LOCALE_VARIATION",
            reviewer_id="reviewer-1",
            reason="permitted by regional policy",
        ),
        result,
    )

    table = build_report_table(result, reviewer_decisions=(decision,))
    text = CsvReportRenderer().render(table)
    reader = csv.DictReader(io.StringIO(text))
    row = next(r for r in reader if r["result_id"] == issue.issue_id)

    # The export contains BOTH the original engine conclusion and the reviewer
    # decision (AC-030); the engine confidence is unchanged (REQ-133).
    assert row["localization_status"] == "MISSING_IN_LOCALE"
    assert row["reviewer_decision"] == "OVERRIDE->EXEMPT_LOCALE_VARIATION"
    assert decision.original_status == "MISSING_IN_LOCALE"
    assert issue.match_confidence is None or float(row["match_confidence"] or 0) == (
        issue.match_confidence or 0
    )
