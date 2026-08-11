"""Unit tests for reviewer decision contracts and service (REQ-128-133)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from reconciliation.application.contracts.reviews import (
    DecisionType,
    ReviewerDecision,
    ReviewerDecisionCommand,
)
from reconciliation.application.errors import ComparisonRejectedError
from reconciliation.application.services.reviewer_decisions import ReviewerDecisionService
from tests.app_builders import localize
from tests.builders import TreeBuilder


def _result(job_id: str = "job-1"):
    src = TreeBuilder("s", "r", node_type="map")
    src.child("r", "a", identity={"id": "a"}).child("r", "b", identity={"id": "b"})
    tgt = TreeBuilder("t", "r", node_type="map")
    tgt.child("r", "a", identity={"id": "a"})
    return localize(src.build(), tgt.build(), job_id=job_id)


def _service() -> ReviewerDecisionService:
    counter = {"n": 0}

    def next_id() -> str:
        counter["n"] += 1
        return f"decision-{counter['n']}"

    return ReviewerDecisionService(
        clock=lambda: datetime(2026, 1, 1, tzinfo=UTC), id_factory=next_id
    )


def test_override_command_requires_replacement() -> None:
    with pytest.raises(ValidationError):
        ReviewerDecisionCommand(
            job_id="j", issue_id="i", decision=DecisionType.OVERRIDE
        )


def test_override_decision_must_differ_from_original() -> None:
    with pytest.raises(ValidationError):
        ReviewerDecision(
            decision_id="d",
            job_id="j",
            issue_id="i",
            decision=DecisionType.OVERRIDE,
            original_status="WRONG_PARENT",
            overridden_status="WRONG_PARENT",
            decided_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_service_captures_original_status() -> None:
    result = _result()
    issue = result.issues[0]
    command = ReviewerDecisionCommand(
        job_id="job-1", issue_id=issue.issue_id, decision=DecisionType.ACCEPT
    )
    decision = _service().record(command, result)
    assert decision.original_status == issue.localization_status.value
    assert decision.decision is DecisionType.ACCEPT
    assert decision.decided_at.year == 2026


def test_service_override_retains_original() -> None:
    result = _result()
    issue = next(i for i in result.issues if i.localization_status.value == "MISSING_IN_LOCALE")
    command = ReviewerDecisionCommand(
        job_id="job-1",
        issue_id=issue.issue_id,
        decision=DecisionType.OVERRIDE,
        overridden_status="EXEMPT_LOCALE_VARIATION",
        reviewer_id="alice",
    )
    decision = _service().record(command, result)
    assert decision.original_status == "MISSING_IN_LOCALE"
    assert decision.overridden_status == "EXEMPT_LOCALE_VARIATION"
    assert decision.reviewer_id == "alice"


def test_service_rejects_unknown_issue() -> None:
    result = _result()
    command = ReviewerDecisionCommand(
        job_id="job-1", issue_id="nope", decision=DecisionType.ACCEPT
    )
    with pytest.raises(ComparisonRejectedError):
        _service().record(command, result)


def test_service_rejects_job_mismatch() -> None:
    result = _result("job-1")
    command = ReviewerDecisionCommand(
        job_id="other", issue_id=result.issues[0].issue_id, decision=DecisionType.DEFER
    )
    with pytest.raises(ComparisonRejectedError):
        _service().record(command, result)
