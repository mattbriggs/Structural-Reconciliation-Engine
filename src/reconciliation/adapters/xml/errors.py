"""Adaptation error taxonomy (SRS §8.8, REQ-006, REQ-015).

Adaptation failures are distinct from core failures: they occur while turning
untrusted external input into a canonical tree. Each carries a stable code so
callers can distinguish a malformed document (``INVALID_INPUT``) from a
security rejection (``UNSAFE_XML``) from a semantic mapping failure
(``DOCUMENT_ADAPTATION_FAILED``).
"""

from __future__ import annotations

from typing import Any


class AdaptationError(Exception):
    """Base class for document-adaptation errors.

    :param message: Human-readable, non-sensitive description.
    :param code: Stable machine code; defaults to the class-level ``code``.
    :param location: Optional input location (line/column/uri) description.
    :param context: Safe structured metadata (no raw untrusted content).
    """

    code: str = "ADAPTATION_ERROR"
    retryable: bool = False

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        location: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or type(self).code
        self.location = location
        self.context: dict[str, Any] = context or {}

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable, safe representation of the error."""
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "location": self.location,
            "context": self.context,
        }


class InputParseError(AdaptationError):
    """Input could not be parsed as well-formed XML."""

    code = "INVALID_INPUT"


class UnsafeXmlError(AdaptationError):
    """Input triggered a rejected unsafe XML construct (XXE, entity bomb, depth)."""

    code = "UNSAFE_XML"


class DocumentAdaptationError(AdaptationError):
    """Parsed XML could not be mapped into a valid canonical tree."""

    code = "DOCUMENT_ADAPTATION_FAILED"
