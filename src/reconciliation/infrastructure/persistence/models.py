"""SQLAlchemy ORM models for persisted results and decisions.

Results and decisions are stored as their serialized versioned JSON contracts
(REQ-152, REQ-211). The persistence layer therefore stores opaque payloads and
has no dependency on the reconciliation *engine* — only on the shared contract
shapes used to (de)serialize at the repository boundary.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for persistence models."""


class JobResultRecord(Base):
    """A stored localization result, keyed by job id."""

    __tablename__ = "job_results"

    job_id: Mapped[str] = mapped_column(String, primary_key=True)
    contract_version: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class ReviewerDecisionRecord(Base):
    """A stored, additive reviewer decision."""

    __tablename__ = "reviewer_decisions"

    decision_id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    issue_id: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
