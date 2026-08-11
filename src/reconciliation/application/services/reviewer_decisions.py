"""Reviewer decision service (REQ-128-133, AC-030).

Creates additive reviewer decisions. The engine's original status is captured
from the stored result so an override can never erase it (REQ-129). Engine
confidence values are never touched (REQ-133). A clock and id factory are
injectable for deterministic testing.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from reconciliation.application.contracts.localization import LocalizationValidationResult
from reconciliation.application.contracts.reviews import (
    DecisionType,
    ReviewerDecision,
    ReviewerDecisionCommand,
)
from reconciliation.application.errors import ComparisonRejectedError


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _uuid() -> str:
    return f"decision-{uuid.uuid4()}"


class ReviewerDecisionService:
    """Records reviewer decisions against a localization result.

    :param clock: Callable returning the decision timestamp.
    :param id_factory: Callable returning a unique decision id.
    """

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] = _utc_now,
        id_factory: Callable[[], str] = _uuid,
    ) -> None:
        self._clock = clock
        self._id_factory = id_factory

    def record(
        self, command: ReviewerDecisionCommand, result: LocalizationValidationResult
    ) -> ReviewerDecision:
        """Create a reviewer decision, capturing the engine's original status.

        :param command: The reviewer's request.
        :param result: The localization result the issue belongs to.
        :returns: An immutable :class:`ReviewerDecision`.
        :raises ComparisonRejectedError: If the issue does not exist in the
            result, or the job ids do not match.
        """
        if command.job_id != result.job_id:
            raise ComparisonRejectedError(
                "decision job id does not match the result",
                context={"command_job": command.job_id, "result_job": result.job_id},
            )
        issue = next((i for i in result.issues if i.issue_id == command.issue_id), None)
        if issue is None:
            raise ComparisonRejectedError(
                "decision references an unknown issue",
                context={"issue_id": command.issue_id},
            )

        overridden = (
            command.overridden_status
            if command.decision is DecisionType.OVERRIDE
            else None
        )
        return ReviewerDecision(
            decision_id=self._id_factory(),
            job_id=command.job_id,
            issue_id=command.issue_id,
            decision=command.decision,
            original_status=issue.localization_status.value,
            overridden_status=overridden,
            reviewer_id=command.reviewer_id,
            reason=command.reason,
            comment=command.comment,
            decided_at=self._clock(),
        )
