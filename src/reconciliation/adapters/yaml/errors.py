"""YAML adaptation errors."""

from __future__ import annotations

from reconciliation.adapters.xml.errors import AdaptationError, InputParseError


class UnsafeYamlError(AdaptationError):
    """YAML input exceeded safety limits or used unsupported constructs."""

    code = "UNSAFE_YAML"


class YamlAdaptationError(AdaptationError):
    """Parsed YAML could not be mapped into a canonical tree."""

    code = "DOCUMENT_ADAPTATION_FAILED"


__all__ = ["AdaptationError", "InputParseError", "UnsafeYamlError", "YamlAdaptationError"]
