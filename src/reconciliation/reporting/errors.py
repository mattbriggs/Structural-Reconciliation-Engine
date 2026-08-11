"""Reporting error taxonomy (SRS §8.8)."""

from __future__ import annotations

from typing import Any


class ReportGenerationError(Exception):
    """A renderer failed to produce an artifact.

    The core/localization result is retained; only the artifact is marked
    failed (SRS §8.8 ``REPORT_GENERATION_FAILED``).
    """

    code = "REPORT_GENERATION_FAILED"
    retryable = False

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = context or {}
