"""Generic XML-to-canonical adaptation (REQ-009-015).

Maps a parsed lxml element tree into a domain-neutral
:class:`~reconciliation.core.contracts.tree.CanonicalTree`, preserving source
locations (REQ-013) and partitioning each element's data into identity,
content, and structural properties. Node references are assigned in document
order so the mapping is deterministic (REQ-203).

This adapter is intentionally vocabulary-agnostic; document-specific identity
rules (DITA keys, href targets, topic ids) are layered by the DITA adapter,
which composes this generic mapping.
"""

from __future__ import annotations

from lxml import etree

from reconciliation.adapters.xml.errors import DocumentAdaptationError
from reconciliation.adapters.xml.parser import SecureXmlParser, XmlSecurityLimits
from reconciliation.core.contracts.tree import (
    CanonicalNode,
    CanonicalTree,
    CanonicalValue,
    SourceLocation,
)
from reconciliation.version import CANONICAL_TREE_CONTRACT_VERSION

#: Attribute names (local or qualified) treated as identity-bearing by default.
_XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
_ID_ATTRIBUTES = ("id", _XML_ID)


def _local_name(tag: str) -> str:
    """Return the namespace-stripped local name of an element tag."""
    return tag.rsplit("}", 1)[-1] if tag.startswith("{") else tag


def _attr_local(name: str) -> str:
    if name == _XML_ID:
        return "xml:id"
    return name.rsplit("}", 1)[-1] if name.startswith("{") else name


class GenericXmlAdapter:
    """Adapts a parsed XML root element into a canonical tree.

    :param contract_version: Canonical tree contract version to stamp on output.
    """

    def __init__(self, *, contract_version: str = CANONICAL_TREE_CONTRACT_VERSION) -> None:
        self._contract_version = contract_version

    def adapt(
        self,
        root: etree._Element,
        *,
        tree_id: str,
        document_uri: str | None = None,
    ) -> CanonicalTree:
        """Adapt ``root`` into a :class:`CanonicalTree`.

        :param root: Parsed, security-validated root element.
        :param tree_id: Stable identifier for the resulting tree.
        :param document_uri: Optional source document URI for locations.
        :returns: An immutable, validated canonical tree.
        :raises DocumentAdaptationError: If the element tree cannot be mapped.
        """
        nodes: dict[str, CanonicalNode] = {}
        tree = root.getroottree()

        def build(element: etree._Element, ref: str, parent_ref: str | None) -> None:
            children = [c for c in element if isinstance(c.tag, str)]
            child_refs = tuple(f"{ref}.{index}" for index in range(len(children)))
            nodes[ref] = self._build_node(
                element, ref, parent_ref, tuple(child_refs), tree, document_uri
            )
            for index, child in enumerate(children):
                build(child, f"{ref}.{index}", ref)

        try:
            build(root, "n", None)
            return CanonicalTree(
                contract_version=self._contract_version,
                tree_id=tree_id,
                root_node_ref="n",
                nodes=nodes,
                metadata={"document_uri": document_uri} if document_uri else {},
            )
        except DocumentAdaptationError:
            raise
        except Exception as exc:
            raise DocumentAdaptationError(
                "failed to adapt XML into a canonical tree",
                location=document_uri,
                context={"detail": str(exc)},
            ) from exc

    def _build_node(
        self,
        element: etree._Element,
        ref: str,
        parent_ref: str | None,
        child_refs: tuple[str, ...],
        tree: etree._ElementTree,
        document_uri: str | None,
    ) -> CanonicalNode:
        identity: dict[str, CanonicalValue] = {}
        structural: dict[str, CanonicalValue] = {}
        for name, value in element.attrib.items():
            local = _attr_local(name)
            structural[local] = value
            if name in _ID_ATTRIBUTES:
                identity["id" if local in ("id", "xml:id") else local] = value

        content: dict[str, CanonicalValue] = {}
        text = (element.text or "").strip()
        if text:
            content["text"] = text

        location = SourceLocation(
            document_uri=document_uri,
            line=element.sourceline if element.sourceline and element.sourceline > 0 else None,
            xpath=tree.getpath(element),
        )
        return CanonicalNode(
            node_ref=ref,
            node_type=_local_name(element.tag),
            parent_ref=parent_ref,
            child_refs=child_refs,
            identity_properties=identity,
            content_properties=content,
            structural_properties=structural,
            source_location=location,
        )


class GenericXmlDocumentAdapter:
    """Parses and adapts generic XML content into a canonical tree."""

    def __init__(
        self,
        *,
        limits: XmlSecurityLimits | None = None,
        contract_version: str = CANONICAL_TREE_CONTRACT_VERSION,
    ) -> None:
        self._parser = SecureXmlParser(limits)
        self._adapter = GenericXmlAdapter(contract_version=contract_version)

    def adapt_document(
        self, data: str | bytes, *, tree_id: str, document_uri: str | None = None
    ) -> CanonicalTree:
        """Parse and adapt XML content into a validated canonical tree."""
        root = self._parser.parse(data, document_uri=document_uri)
        return self._adapter.adapt(root, tree_id=tree_id, document_uri=document_uri)
