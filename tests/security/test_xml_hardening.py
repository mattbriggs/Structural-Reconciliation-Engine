"""Security tests for XML hardening (REQ-216-218).

Verifies the parser defeats the classic XML attacks before canonicalization:
external entities (XXE), entity-expansion bombs, external DTD loading, and
resource exhaustion via size / depth / node count.
"""

from __future__ import annotations

import pytest

from reconciliation.adapters.xml.errors import InputParseError, UnsafeXmlError
from reconciliation.adapters.xml.parser import SecureXmlParser, XmlSecurityLimits

pytestmark = pytest.mark.security


def test_xxe_external_entity_is_rejected() -> None:
    xxe = (
        '<?xml version="1.0"?>'
        '<!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]>'
        "<r>&x;</r>"
    )
    with pytest.raises(UnsafeXmlError) as exc:
        SecureXmlParser().parse(xxe)
    assert exc.value.code == "UNSAFE_XML"


def test_billion_laughs_entity_expansion_is_rejected() -> None:
    lol = (
        '<?xml version="1.0"?>'
        "<!DOCTYPE l ["
        '<!ENTITY a "aaaaaaaaaa">'
        '<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">'
        '<!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">'
        "]>"
        "<l>&c;</l>"
    )
    with pytest.raises(UnsafeXmlError):
        SecureXmlParser().parse(lol)


def test_external_parameter_entity_dtd_not_fetched() -> None:
    # A SYSTEM external DTD reference must not be loaded from the network/disk.
    doc = (
        '<?xml version="1.0"?>'
        '<!DOCTYPE r SYSTEM "http://127.0.0.1:9/evil.dtd">'
        "<r>ok</r>"
    )
    # Either the parser refuses resolution (UnsafeXmlError) or parses without
    # fetching the DTD; in both cases no network access occurs and the document
    # body is intact.
    try:
        root = SecureXmlParser().parse(doc)
        assert (root.text or "").strip() == "ok"
    except UnsafeXmlError as exc:
        assert exc.code == "UNSAFE_XML"


def test_size_limit_enforced() -> None:
    big = "<r>" + ("x" * 2000) + "</r>"
    with pytest.raises(UnsafeXmlError):
        SecureXmlParser(XmlSecurityLimits(max_bytes=100)).parse(big)


def test_depth_limit_enforced_below_libxml2_default() -> None:
    # Depth chosen under libxml2's own hard limit so our configured cap fires.
    depth = 60
    doc = "<a>" * depth + "</a>" * depth
    with pytest.raises(UnsafeXmlError) as exc:
        SecureXmlParser(XmlSecurityLimits(max_depth=40)).parse(doc)
    assert exc.value.code == "UNSAFE_XML"


def test_node_count_limit_enforced() -> None:
    doc = "<r>" + "".join(f"<c{i}/>" for i in range(50)) + "</r>"
    with pytest.raises(UnsafeXmlError):
        SecureXmlParser(XmlSecurityLimits(max_nodes=10)).parse(doc)


def test_malformed_xml_is_input_parse_error() -> None:
    with pytest.raises(InputParseError) as exc:
        SecureXmlParser().parse("<a><b></a>")
    assert exc.value.code == "INVALID_INPUT"


def test_well_formed_document_parses() -> None:
    root = SecureXmlParser().parse("<map><topicref href='a.dita'/></map>")
    assert root.tag == "map"
