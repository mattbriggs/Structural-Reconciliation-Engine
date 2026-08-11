"""Reviewer decision contracts (REQ-128-133, REQ-213, AC-030).

Reviewer decisions are *additive*: they record a human disposition without
overwriting the engine's conclusion (REQ-129, REQ-213) and never alter engine
confidence values (REQ-133). An ``OVERRIDE`` must retain the original status so
an export can show both the engine conclusion and the reviewer decision
(AC-030).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field, model_validator

from reconciliation.core.contracts.base import StrictModel


class DecisionType(str, Enum):
    """Reviewer decision dispositions (REQ-128)."""

    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    OVERRIDE = "OVERRIDE"
    DEFER = "DEFER"
    UNRESOLVED = "UNRESOLVED"


class ReviewerDecisionCommand(StrictModel):
    """A request to record a reviewer decision on an issue.

    :ivar job_id: The comparison job.
    :ivar issue_id: The localization issue the decision applies to.
    :ivar decision: The reviewer disposition.
    :ivar reviewer_id: Reviewer identity when supplied (REQ-130).
    :ivar reason: Reason for the decision.
    :ivar comment: Optional free-text comment.
    :ivar overridden_status: For ``OVERRIDE``, the reviewer's replacement
        status string; the engine's original status is captured separately.
    """

    job_id: str = Field(min_length=1)
    issue_id: str = Field(min_length=1)
    decision: DecisionType
    reviewer_id: str | None = None
    reason: str | None = None
    comment: str | None = None
    overridden_status: str | None = None

    @model_validator(mode="after")
    def _override_requires_replacement(self) -> ReviewerDecisionCommand:
        if self.decision is DecisionType.OVERRIDE and not self.overridden_status:
            raise ValueError("an OVERRIDE decision must supply a replacement status")
        return self


class ReviewerDecision(StrictModel):
    """A recorded, immutable reviewer decision (REQ-129, REQ-130, REQ-213).

    :ivar decision_id: Stable identifier.
    :ivar job_id: The comparison job.
    :ivar issue_id: The localization issue this decision concerns.
    :ivar decision: The reviewer disposition.
    :ivar original_status: The engine's original localization status, retained
        so it is never lost to an override (REQ-129, AC-030).
    :ivar overridden_status: The reviewer's replacement status for an override.
    :ivar reviewer_id: Reviewer identity when supplied.
    :ivar reason: Reason for the decision.
    :ivar comment: Optional free-text comment.
    :ivar decided_at: Timestamp the decision was recorded (REQ-130).
    """

    decision_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    issue_id: str = Field(min_length=1)
    decision: DecisionType
    original_status: str
    overridden_status: str | None = None
    reviewer_id: str | None = None
    reason: str | None = None
    comment: str | None = None
    decided_at: datetime

    @model_validator(mode="after")
    def _override_retains_original(self) -> ReviewerDecision:
        # REQ-129: an override retains the original engine conclusion.
        if self.decision is DecisionType.OVERRIDE:
            if not self.overridden_status:
                raise ValueError("an OVERRIDE decision must record a replacement status")
            if self.overridden_status == self.original_status:
                raise ValueError("an OVERRIDE must differ from the original engine status")
        return self
