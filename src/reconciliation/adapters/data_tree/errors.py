"""Errors for generic parsed-data canonicalization."""

from __future__ import annotations

from reconciliation.adapters.xml.errors import AdaptationError


class DataTreeAdaptationError(AdaptationError):
    """Parsed data could not be mapped into a canonical tree."""

    code = "DOCUMENT_ADAPTATION_FAILED"
