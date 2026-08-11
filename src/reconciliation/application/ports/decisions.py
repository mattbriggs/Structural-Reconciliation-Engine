"""Reviewer decision repository port (REQ-213, REQ-250).

Reviewer decisions are additive; the repository only appends and lists them,
never mutating or deleting engine output (REQ-213).
"""

from __future__ import annotations

from typing import Protocol

from reconciliation.application.contracts.reviews import ReviewerDecision


class ReviewerDecisionRepository(Protocol):
    """Appends and lists reviewer decisions for a job."""

    def add(self, decision: ReviewerDecision) -> None:
        """Append a reviewer decision."""
        ...

    def list_for_job(self, job_id: str) -> tuple[ReviewerDecision, ...]:
        """Return all decisions for ``job_id`` in insertion order."""
        ...
