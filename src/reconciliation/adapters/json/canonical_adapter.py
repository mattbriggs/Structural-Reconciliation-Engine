"""Generic JSON-to-canonical document adapter."""

from __future__ import annotations

from reconciliation.adapters.data_tree import DataTreeAdapter
from reconciliation.adapters.data_tree.errors import DataTreeAdaptationError
from reconciliation.adapters.json.errors import JsonAdaptationError
from reconciliation.adapters.json.parser import JsonSecurityLimits, SecureJsonParser
from reconciliation.core.contracts.tree import CanonicalTree
from reconciliation.version import CANONICAL_TREE_CONTRACT_VERSION


class JsonDocumentAdapter:
    """Parse JSON and adapt it into a canonical tree."""

    def __init__(
        self,
        *,
        limits: JsonSecurityLimits | None = None,
        contract_version: str = CANONICAL_TREE_CONTRACT_VERSION,
    ) -> None:
        self._parser = SecureJsonParser(limits)
        self._adapter = DataTreeAdapter(
            contract_version=contract_version,
            source_format="json",
        )

    def adapt_document(
        self, data: str | bytes, *, tree_id: str, document_uri: str | None = None
    ) -> CanonicalTree:
        """Parse and adapt JSON content into a validated canonical tree."""
        parsed = self._parser.parse(data, document_uri=document_uri)
        try:
            return self._adapter.adapt(parsed, tree_id=tree_id, document_uri=document_uri)
        except DataTreeAdaptationError as exc:
            raise JsonAdaptationError(
                exc.message,
                location=exc.location or document_uri,
                context=exc.context,
            ) from exc
