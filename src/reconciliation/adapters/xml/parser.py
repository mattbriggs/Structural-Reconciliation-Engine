"""Hardened XML parsing for untrusted input (REQ-216-218).

XML input is treated as untrusted. The parser is configured to defeat the
classic XML attacks *before* canonicalization:

* **XXE / external entities** — external entity resolution is disabled and all
  resolution is blocked by a no-op resolver; the parser never touches the
  network (REQ-217).
* **Entity-expansion (billion laughs)** — internal entities are not expanded,
  and any residual entity reference in the parsed tree is rejected (REQ-218).
* **External DTD loading** — disabled; a DOCTYPE may be present (DITA documents
  carry one) but its external subset is never fetched.
* **Resource exhaustion** — input byte size, element nesting depth, and total
  node count are bounded (REQ-196, REQ-218).

Enabling entity resolution would require an explicitly-secured profile
(REQ-217); this module never does so implicitly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lxml import etree

from reconciliation.adapters.xml.errors import InputParseError, UnsafeXmlError


@dataclass(frozen=True)
class XmlSecurityLimits:
    """Bounds enforced on untrusted XML input.

    :ivar max_bytes: Maximum serialized input size.
    :ivar max_depth: Maximum element nesting depth (root = 1).
    :ivar max_nodes: Maximum total element count.
    """

    max_bytes: int = 10_000_000
    max_depth: int = 100
    max_nodes: int = 100_000


class _BlockingResolver(etree.Resolver):  # type: ignore[misc]
    """Resolver that refuses every external reference (belt-and-braces XXE guard)."""

    def resolve(self, system_url: str, public_id: str, context: Any) -> Any:
        raise UnsafeXmlError(
            "external entity or DTD resolution is disabled",
            context={"system_url": system_url or "", "public_id": public_id or ""},
        )


class SecureXmlParser:
    """Parses untrusted XML into an lxml element tree under strict limits.

    :param limits: Resource limits; defaults to :class:`XmlSecurityLimits`.
    """

    def __init__(self, limits: XmlSecurityLimits | None = None) -> None:
        self._limits = limits or XmlSecurityLimits()

    def _new_parser(self) -> etree.XMLParser:
        parser = etree.XMLParser(
            resolve_entities=False,  # no entity expansion (REQ-218)
            no_network=True,  # no network access (REQ-217, REQ-235)
            load_dtd=False,  # never load external DTD subset
            dtd_validation=False,
            huge_tree=False,  # keep libxml2's built-in guards active
            recover=False,  # reject malformed input rather than guessing
        )
        parser.resolvers.add(_BlockingResolver())
        return parser

    def parse(self, data: str | bytes, *, document_uri: str | None = None) -> etree._Element:
        """Parse ``data`` and return the validated root element.

        :param data: XML text or bytes.
        :param document_uri: Optional URI recorded for diagnostics only.
        :returns: The parsed root :class:`lxml.etree._Element`.
        :raises InputParseError: If the input is not well-formed XML.
        :raises UnsafeXmlError: If a size/depth/node limit is exceeded or an
            unsafe construct (entity reference, external resolution) is present.
        """
        raw = data.encode("utf-8") if isinstance(data, str) else data
        if len(raw) > self._limits.max_bytes:
            raise UnsafeXmlError(
                "XML input exceeds the configured maximum size",
                location=document_uri,
                context={"bytes": len(raw), "limit": self._limits.max_bytes},
            )

        try:
            root = etree.fromstring(raw, parser=self._new_parser())
        except etree.XMLSyntaxError as exc:
            raise InputParseError(
                "input is not well-formed XML",
                location=document_uri,
                context={"detail": str(exc)},
            ) from exc

        self._reject_entities(root, document_uri)
        self._enforce_structure_limits(root, document_uri)
        return root

    def _reject_entities(self, root: etree._Element, document_uri: str | None) -> None:
        # With resolve_entities=False, an entity reference survives as an Entity
        # node; reject it rather than passing it downstream (REQ-218).
        for node in root.iter():
            # Entity / comment / PI nodes have a non-str tag callable.
            if not isinstance(node.tag, str) and node.tag is etree.Entity:
                raise UnsafeXmlError(
                    "entity references are not permitted in untrusted input",
                    location=document_uri,
                    context={"entity": str(node.text or node.tag)},
                )

    def _enforce_structure_limits(
        self, root: etree._Element, document_uri: str | None
    ) -> None:
        node_count = 0
        for node in root.iter():
            if not isinstance(node.tag, str):
                continue
            node_count += 1
            if node_count > self._limits.max_nodes:
                raise UnsafeXmlError(
                    "XML input exceeds the configured maximum node count",
                    location=document_uri,
                    context={"limit": self._limits.max_nodes},
                )
            depth = 1
            ancestor = node.getparent()
            while ancestor is not None:
                depth += 1
                if depth > self._limits.max_depth:
                    raise UnsafeXmlError(
                        "XML input exceeds the configured maximum nesting depth",
                        location=document_uri,
                        context={"limit": self._limits.max_depth},
                    )
                ancestor = ancestor.getparent()
