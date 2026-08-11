"""SQLite implementation of the comparison result repository (REQ-211).

Stores the localization result as its serialized versioned JSON contract and
reconstructs it on read, round-tripping exactly. Implements
:class:`~reconciliation.application.ports.results.ComparisonResultRepository`.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from reconciliation.application.contracts.localization import LocalizationValidationResult
from reconciliation.application.ports.results import RepositoryError
from reconciliation.infrastructure.persistence.models import JobResultRecord


class SqliteComparisonResultRepository:
    """Persists localization results in a relational store."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def save(self, result: LocalizationValidationResult) -> None:
        """Persist (upsert) a localization result by job id."""
        try:
            with self._session_factory() as session:
                existing = session.get(JobResultRecord, result.job_id)
                payload = result.model_dump_json()
                if existing is None:
                    session.add(
                        JobResultRecord(
                            job_id=result.job_id,
                            contract_version=result.contract_version,
                            payload=payload,
                            created_at=datetime.now(UTC),
                        )
                    )
                else:
                    existing.payload = payload
                    existing.contract_version = result.contract_version
                session.commit()
        except Exception as exc:  # normalized into a boundary error
            raise RepositoryError(f"failed to save result {result.job_id!r}: {exc}") from exc

    def get(self, job_id: str) -> LocalizationValidationResult | None:
        """Return the stored result for ``job_id``, or ``None``."""
        try:
            with self._session_factory() as session:
                record = session.get(JobResultRecord, job_id)
                if record is None:
                    return None
                return LocalizationValidationResult.model_validate_json(record.payload)
        except Exception as exc:
            raise RepositoryError(f"failed to load result {job_id!r}: {exc}") from exc
