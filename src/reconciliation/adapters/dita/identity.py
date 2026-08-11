"""DITA identity-signal extraction (REQ-033, REQ-034).

Extracts the identity and label signals a DITA map carries on each element:
``xml:id``/``@id``, ``@keys``, the normalized ``@href`` target, and the
navigation title (``@navtitle`` or a ``topicmeta/navtitle`` child). These feed
the canonical node's ``identity_properties`` and ``content_properties`` so the
core can match on locale-stable identity rather than translated text (REQ-113).
"""

from __future__ import annotations

from lxml import etree

from reconciliation.adapters.dita.normalization import normalize_href, normalize_keys

_XML_ID = "{http://www.w3.org/XML/1998/namespace}id"


def _local(tag: object) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) and tag.startswith("{") else str(tag)


def extract_identity(element: etree._Element) -> dict[str, str]:
    """Return DITA identity properties for one element.

    :param element: The DITA element (e.g. ``topicref``).
    :returns: A mapping with any of ``id``, ``keys``, ``href`` that are present.
    """
    identity: dict[str, str] = {}
    node_id = element.get("id") or element.get(_XML_ID)
    if node_id:
        identity["id"] = node_id
    keys = element.get("keys")
    if keys:
        normalized = normalize_keys(keys)
        if normalized:
            identity["keys"] = " ".join(normalized)
    href = element.get("href")
    if href:
        identity["href"] = normalize_href(href)
    return identity


def extract_navtitle(element: etree._Element) -> str | None:
    """Return the navigation title of a DITA element, if any.

    Prefers the ``@navtitle`` attribute, then a ``topicmeta/navtitle`` child.

    :param element: The DITA element.
    :returns: The navtitle text, or ``None`` when absent.
    """
    nav = element.get("navtitle")
    if nav and str(nav).strip():
        return str(nav).strip()
    for child in element:
        if _local(child.tag) == "topicmeta":
            for meta_child in child:
                if _local(meta_child.tag) == "navtitle":
                    text = str(meta_child.text or "").strip()
                    if text:
                        return text
    return None
