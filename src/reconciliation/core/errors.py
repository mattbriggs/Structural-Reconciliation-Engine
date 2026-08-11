"""Core error taxonomy.

Errors are defined by *boundary* rather than as generic exceptions so that
callers can map failures to stable machine codes and decide retryability
(REQ-006, REQ-179, REQ-180). Every core exception exposes:

* ``code`` — a stable, machine-readable error code (matches the SRS error
  table in §8.8),
* ``retryable`` — whether retrying the identical request could succeed,
* ``correlation_id`` — propagated tracing id when known (REQ-245),
* ``context`` — safe, non-sensitive structured detail (REQ-243).

The context must never contain raw source or translated content; redaction is
the caller's responsibility but the taxonomy makes the safe-by-default intent
explicit.
"""

from __future__ import annotations

from typing import Any


class ReconciliationError(Exception):
    """Base class for all core reconciliation errors.

    :param message: Human-readable, non-sensitive description.
    :param code: Stable machine code; defaults to the class-level ``code``.
    :param retryable: Whether an identical retry could succeed.
    :param correlation_id: Tracing identifier when available.
    :param context: Safe structured metadata (no raw content).
    """

    #: Default stable machine code; subclasses override.
    code: str = "RECONCILIATION_ERROR"
    #: Default retryability for this error family.
    default_retryable: bool = False

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        retryable: bool | None = None,
        correlation_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or type(self).code
        self.retryable = self.default_retryable if retryable is None else retryable
        self.correlation_id = correlation_id
        self.context: dict[str, Any] = context or {}

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable, safe representation of the error."""
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "correlation_id": self.correlation_id,
            "context": self.context,
        }


# --- Core validation boundary (REQ-005, REQ-165-170, REQ-280-283) ---------


class InvalidTreeError(ReconciliationError):
    """A canonical tree violates a structural invariant."""

    code = "INVALID_TREE"


class InvalidProfileError(ReconciliationError):
    """A profile is malformed, conflicting, or references unknown identifiers."""

    code = "INVALID_PROFILE"


class UnsupportedContractError(ReconciliationError):
    """A contract version is not supported by this engine."""

    code = "UNSUPPORTED_CONTRACT"


# --- Core pipeline stages -------------------------------------------------


class NormalizationError(ReconciliationError):
    """Normalization failed or rules could not be applied coherently."""

    code = "NORMALIZATION_FAILED"


class MatchingError(ReconciliationError):
    """The matcher could not complete."""

    code = "MATCHING_FAILED"


class AlignmentError(ReconciliationError):
    """Structural alignment could not complete."""

    code = "ALIGNMENT_FAILED"


class ClassificationError(ReconciliationError):
    """Operation classification failed."""

    code = "CLASSIFICATION_FAILED"


class RootCauseError(ReconciliationError):
    """Root-cause analysis failed."""

    code = "ROOT_CAUSE_FAILED"


# --- Resource governance (REQ-196, REQ-200) -------------------------------


class ResourceLimitExceededError(ReconciliationError):
    """A configured resource limit was exceeded during reconciliation."""

    code = "RESOURCE_LIMIT_EXCEEDED"
    default_retryable = False
