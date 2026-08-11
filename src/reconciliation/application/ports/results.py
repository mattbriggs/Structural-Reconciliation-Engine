"""Comparison result repository port (REQ-211, REQ-250).

Persists immutable localization results so a report can be reconstructed later
(REQ-211). Implementations must round-trip the versioned contract exactly.
"""

from __future__ import annotations

from typing import Protocol

from reconciliation.application.contracts.localization import LocalizationValidationResult


class RepositoryError(Exception):
    """A repository operation failed."""

    code = "REPOSITORY_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ComparisonResultRepository(Protocol):
    """Stores and retrieves immutable localization results by job id."""

    def save(self, result: LocalizationValidationResult) -> None:
        """Persist a localization result (idempotent by job id)."""
        ...

    def get(self, job_id: str) -> LocalizationValidationResult | None:
        """Return the stored result for ``job_id``, or ``None`` if absent."""
        ...
