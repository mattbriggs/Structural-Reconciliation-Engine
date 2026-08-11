"""Document adapter port (REQ-011, REQ-230).

The orchestration layer depends on this Protocol, not on any concrete XML/DITA
adapter, so new document models can be added without changing the pipeline
(AC-032). The DITA and generic XML adapters satisfy it structurally.
"""

from __future__ import annotations

from typing import Protocol

from reconciliation.core.contracts.tree import CanonicalTree


class DocumentAdapter(Protocol):
    """Converts raw document content into a canonical tree."""

    def adapt_document(
        self, data: str | bytes, *, tree_id: str, document_uri: str | None = None
    ) -> CanonicalTree:
        """Parse and adapt document content into a validated canonical tree."""
        ...
