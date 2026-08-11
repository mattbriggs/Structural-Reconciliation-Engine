"""Tests for the observability report (REQ-244, REQ-246)."""

from __future__ import annotations

import io
import json
from collections.abc import Iterator

import pytest
import structlog

from reconciliation.application.contracts.jobs import ComparisonRequest, ComparisonState
from reconciliation.application.orchestration.comparison_job import ComparisonJobService
from reconciliation.application.services.observability import build_observability_report
from reconciliation.delivery.composition import build_default_registry
from reconciliation.infrastructure.logging import configure_logging, get_logger

SRC = '<map><topicref keys="a" href="a.dita"/><topicref keys="gone" href="g.dita"/></map>'
LOC = '<map><topicref keys="a" href="a.dita"/></map>'
CLEAN = '<map><topicref keys="a" href="a.dita"/></map>'


@pytest.fixture(autouse=True)
def _reset_structlog() -> Iterator[None]:
    yield
    structlog.reset_defaults()


def _run(source: str, locale: str, *, job_id: str = "obs"):
    service = ComparisonJobService(build_default_registry())
    return service.run(
        ComparisonRequest(
            source_content=source, locale_content=locale, locale="fr-FR",
            document_profile_id="dita-map-v1", job_id=job_id,
        )
    )


def test_report_counts_for_completed_with_issues() -> None:
    outcome = _run(SRC, LOC)
    report = build_observability_report(outcome.record, outcome.result)
    assert report.outcome == "COMPLETED"
    assert report.technical_failure is False
    assert report.completed_with_issues is True  # MISSING is an ERROR
    assert report.match_count == 2
    assert report.operation_count >= 1
    assert report.source_node_count == 3
    assert report.stage_durations_ms  # timings present


def test_report_clean_comparison_has_no_blocking_issues() -> None:
    outcome = _run(CLEAN, CLEAN, job_id="clean")
    report = build_observability_report(outcome.record, outcome.result)
    assert report.outcome == "COMPLETED"
    assert report.completed_with_issues is False


def test_report_distinguishes_technical_failure() -> None:
    # REQ-246: a rejected job is a technical failure, not a completed comparison.
    outcome = ComparisonJobService(build_default_registry()).run(
        ComparisonRequest(
            source_content=SRC, locale_content=LOC, locale="fr-FR",
            document_profile_id="no-such-profile", job_id="rej",
        )
    )
    report = build_observability_report(outcome.record, outcome.result)
    assert outcome.record.state is ComparisonState.REJECTED
    assert report.technical_failure is True
    assert report.completed_with_issues is False
    assert report.match_count == 0


def test_service_emits_observability_events_when_logger_configured() -> None:
    stream = io.StringIO()
    configure_logging(json_output=True, stream=stream)
    service = ComparisonJobService(build_default_registry(), logger=get_logger("job"))
    service.run(
        ComparisonRequest(
            source_content=SRC, locale_content=LOC, locale="fr-FR",
            document_profile_id="dita-map-v1", job_id="emit-1",
        )
    )
    events = [json.loads(line) for line in stream.getvalue().strip().splitlines()]
    outcome_events = [e for e in events if e.get("event") == "comparison.outcome"]
    stage_events = [e for e in events if e.get("event") == "comparison.stage"]
    assert outcome_events and stage_events
    outcome_event = outcome_events[0]
    assert outcome_event["correlation_id"] == "corr-emit-1"
    assert outcome_event["match_count"] == 2
    # No content leaks into observability logs (REQ-243).
    assert not any(k in outcome_event for k in ("source_content", "text", "navtitle"))
