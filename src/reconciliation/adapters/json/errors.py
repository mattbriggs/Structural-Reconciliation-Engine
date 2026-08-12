"""JSON adaptation errors."""

from __future__ import annotations

from reconciliation.adapters.xml.errors import AdaptationError, InputParseError


class UnsafeJsonError(AdaptationError):
    """JSON input exceeded safety limits or used unsupported constructs."""

    code = "UNSAFE_JSON"


class JsonAdaptationError(AdaptationError):
    """Parsed JSON could not be mapped into a canonical tree."""

    code = "DOCUMENT_ADAPTATION_FAILED"


__all__ = ["AdaptationError", "InputParseError", "JsonAdaptationError", "UnsafeJsonError"]
