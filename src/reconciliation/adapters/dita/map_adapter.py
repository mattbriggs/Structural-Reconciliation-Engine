"""DITA map adapter (REQ-011-013, REQ-033).

Parses a DITA map with the hardened XML parser and maps it to a canonical tree.
Each element's canonical identity is resolved from DITA's locale-stable signals
in priority order ``@id`` > ``@keys`` > ``@href`` and exposed as the canonical
``id`` property so the core's persistent-identifier matching (REQ-034) works
across source and locale without depending on translated navigation titles
(REQ-113). The original ``keys``/``href`` values are retained as identity
properties for evidence and audit.
"""

from __future__ import annotations

from lxml import etree

from reconciliation.adapters.dita.identity import extract_identity, extract_navtitle
from reconciliation.adapters.xml.canonical_adapter import _attr_local, _local_name
from reconciliation.adapters.xml.errors import DocumentAdaptationError
from reconciliation.adapters.xml.parser import SecureXmlParser, XmlSecurityLimits
from reconciliation.core.contracts.tree import (
    CanonicalNode,
    CanonicalTree,
    CanonicalValue,
    SourceLocation,
)
from reconciliation.version import CANONICAL_TREE_CONTRACT_VERSION


def _canonical_id(identity: dict[str, str]) -> str | None:
    """Resolve a single canonical identity from DITA signals (id > keys > href)."""
    if "id" in identity:
        return identity["id"]
    if "keys" in identity:
        return f"keys:{identity['keys']}"
    if "href" in identity:
        return f"href:{identity['href']}"
    return None


class DitaMapAdapter:
    """Adapts a DITA map document into a canonical tree.

    :param limits: XML security limits applied during parsing.
    :param contract_version: Canonical tree contract version to stamp on output.
    """

    def __init__(
        self,
        *,
        limits: XmlSecurityLimits | None = None,
        contract_version: str = CANONICAL_TREE_CONTRACT_VERSION,
    ) -> None:
        self._parser = SecureXmlParser(limits)
        self._contract_version = contract_version

    def adapt_document(
        self, data: str | bytes, *, tree_id: str, document_uri: str | None = None
    ) -> CanonicalTree:
        """Parse and adapt a DITA map document into a canonical tree.

        :param data: The DITA map source (text or bytes).
        :param tree_id: Stable identifier for the resulting tree.
        :param document_uri: Optional source document URI for locations.
        :returns: An immutable, validated canonical tree.
        :raises InputParseError: If the input is not well-formed XML.
        :raises UnsafeXmlError: If an unsafe construct or limit is hit.
        :raises DocumentAdaptationError: If mapping fails.
        """
        root = self._parser.parse(data, document_uri=document_uri)
        return self.adapt(root, tree_id=tree_id, document_uri=document_uri)

    def adapt(
        self, root: etree._Element, *, tree_id: str, document_uri: str | None = None
    ) -> CanonicalTree:
        """Adapt an already-parsed DITA map root element into a canonical tree."""
        nodes: dict[str, CanonicalNode] = {}
        tree = root.getroottree()

        def build(element: etree._Element, ref: str, parent_ref: str | None) -> None:
            children = [c for c in element if isinstance(c.tag, str) and not _is_metadata(c)]
            child_refs = tuple(f"{ref}.{i}" for i in range(len(children)))
            nodes[ref] = self._build_node(
                element, ref, parent_ref, child_refs, tree, document_uri
            )
            for i, child in enumerate(children):
                build(child, f"{ref}.{i}", ref)

        try:
            build(root, "n", None)
            return CanonicalTree(
                contract_version=self._contract_version,
                tree_id=tree_id,
                root_node_ref="n",
                nodes=nodes,
                metadata={"document_uri": document_uri, "profile": "dita-map-v1"}
                if document_uri
                else {"profile": "dita-map-v1"},
            )
        except DocumentAdaptationError:
            raise
        except Exception as exc:
            raise DocumentAdaptationError(
                "failed to adapt DITA map into a canonical tree",
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
        identity: dict[str, CanonicalValue] = dict(extract_identity(element))
        canonical_id = _canonical_id({k: str(v) for k, v in identity.items()})
        if canonical_id is not None:
            identity["id"] = canonical_id

        structural: dict[str, CanonicalValue] = {
            _attr_local(name): value for name, value in element.attrib.items()
        }

        content: dict[str, CanonicalValue] = {}
        navtitle = extract_navtitle(element)
        if navtitle:
            content["navtitle"] = navtitle
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


def _is_metadata(element: etree._Element) -> bool:
    """True for DITA metadata elements folded into the parent (e.g. topicmeta)."""
    return _local_name(element.tag) == "topicmeta"
