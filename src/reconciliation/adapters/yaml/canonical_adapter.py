"""Generic YAML-to-canonical document adapter."""

from __future__ import annotations

from reconciliation.adapters.data_tree import DataTreeAdapter
from reconciliation.adapters.data_tree.errors import DataTreeAdaptationError
from reconciliation.adapters.yaml.errors import YamlAdaptationError
from reconciliation.adapters.yaml.parser import SecureYamlParser, YamlSecurityLimits
from reconciliation.core.contracts.tree import CanonicalTree
from reconciliation.version import CANONICAL_TREE_CONTRACT_VERSION


class YamlDocumentAdapter:
    """Parse YAML and adapt it into a canonical tree."""

    def __init__(
        self,
        *,
        limits: YamlSecurityLimits | None = None,
        contract_version: str = CANONICAL_TREE_CONTRACT_VERSION,
    ) -> None:
        self._parser = SecureYamlParser(limits)
        self._adapter = DataTreeAdapter(
            contract_version=contract_version,
            source_format="yaml",
        )

    def adapt_document(
        self, data: str | bytes, *, tree_id: str, document_uri: str | None = None
    ) -> CanonicalTree:
        """Parse and adapt YAML content into a validated canonical tree."""
        parsed = self._parser.parse(data, document_uri=document_uri)
        try:
            return self._adapter.adapt(parsed, tree_id=tree_id, document_uri=document_uri)
        except DataTreeAdaptationError as exc:
            raise YamlAdaptationError(
                exc.message,
                location=exc.location or document_uri,
                context=exc.context,
            ) from exc
