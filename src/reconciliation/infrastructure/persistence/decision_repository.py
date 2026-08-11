"""SQLite implementation of the reviewer decision repository (REQ-213).

Decisions are append-only; the repository never updates or deletes an existing
decision, preserving the audit trail. Implements
:class:`~reconciliation.application.ports.decisions.ReviewerDecisionRepository`.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from reconciliation.application.contracts.reviews import ReviewerDecision
from reconciliation.application.ports.results import RepositoryError
from reconciliation.infrastructure.persistence.models import ReviewerDecisionRecord


class SqliteReviewerDecisionRepository:
    """Appends and lists reviewer decisions in a relational store."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def add(self, decision: ReviewerDecision) -> None:
        """Append a reviewer decision (rejects duplicate ids)."""
        try:
            with self._session_factory() as session:
                if session.get(ReviewerDecisionRecord, decision.decision_id) is not None:
                    raise RepositoryError(
                        f"reviewer decision {decision.decision_id!r} already exists"
                    )
                session.add(
                    ReviewerDecisionRecord(
                        decision_id=decision.decision_id,
                        job_id=decision.job_id,
                        issue_id=decision.issue_id,
                        payload=decision.model_dump_json(),
                        created_at=datetime.now(UTC),
                    )
                )
                session.commit()
        except RepositoryError:
            raise
        except Exception as exc:
            raise RepositoryError(f"failed to add decision: {exc}") from exc

    def list_for_job(self, job_id: str) -> tuple[ReviewerDecision, ...]:
        """Return all decisions for ``job_id`` in insertion order."""
        try:
            with self._session_factory() as session:
                stmt = (
                    select(ReviewerDecisionRecord)
                    .where(ReviewerDecisionRecord.job_id == job_id)
                    .order_by(ReviewerDecisionRecord.created_at, ReviewerDecisionRecord.decision_id)
                )
                records = session.scalars(stmt).all()
                return tuple(
                    ReviewerDecision.model_validate_json(record.payload) for record in records
                )
        except Exception as exc:
            raise RepositoryError(f"failed to list decisions for {job_id!r}: {exc}") from exc
