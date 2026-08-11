"""Application-layer error taxonomy.

Distinct from core and adaptation errors: these arise while interpreting a
reconciliation result into localization terms, applying policy, or planning
recommendations. Each carries a stable code and safe context.
"""

from __future__ import annotations

from typing import Any


class ApplicationError(Exception):
    """Base class for application-layer errors."""

    code: str = "APPLICATION_ERROR"
    retryable: bool = False

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or type(self).code
        self.context: dict[str, Any] = context or {}

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable, safe representation of the error."""
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "context": self.context,
        }


class ComparisonRejectedError(ApplicationError):
    """A comparison request was rejected before or during interpretation."""

    code = "COMPARISON_REJECTED"


class InvalidPolicyError(ApplicationError):
    """A locale-variation policy is malformed or conflicting (REQ-109)."""

    code = "INVALID_POLICY"


class RecommendationError(ApplicationError):
    """A repair recommendation could not be produced safely."""

    code = "RECOMMENDATION_ERROR"
