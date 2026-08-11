"""Unit tests for the generic XML-to-canonical adapter (REQ-009-015)."""

from __future__ import annotations

from reconciliation.adapters.xml.canonical_adapter import GenericXmlAdapter
from reconciliation.adapters.xml.parser import SecureXmlParser
from reconciliation.core.validation.tree_validator import validate_tree_result


def _adapt(xml: str):
    root = SecureXmlParser().parse(xml)
    return GenericXmlAdapter().adapt(root, tree_id="t", document_uri="doc.xml")


def test_adapt_produces_valid_canonical_tree() -> None:
    tree = _adapt("<map><topicref id='a'/><topicref id='b'/></map>")
    assert validate_tree_result(tree).valid
    assert tree.nodes["n"].node_type == "map"
    assert len(tree.nodes) == 3


def test_attributes_and_text_and_id_mapped() -> None:
    tree = _adapt("<map><topicref id='a' href='a.dita'>Hello</topicref></map>")
    node = tree.nodes["n.0"]
    assert node.identity_properties["id"] == "a"
    assert node.structural_properties["href"] == "a.dita"
    assert node.content_properties["text"] == "Hello"


def test_xml_id_is_recognized_as_identity() -> None:
    tree = _adapt("<map><topicref xml:id='x'/></map>")
    assert tree.nodes["n.0"].identity_properties["id"] == "x"
    assert "xml:id" in tree.nodes["n.0"].structural_properties


def test_source_location_preserved() -> None:
    tree = _adapt("<map>\n  <topicref id='a'/>\n</map>")
    loc = tree.nodes["n.0"].source_location
    assert loc is not None
    assert loc.document_uri == "doc.xml"
    assert loc.xpath and loc.xpath.endswith("topicref")
    assert loc.line == 2


def test_utf8_content_preserved() -> None:
    tree = _adapt("<map><topicref>Introducción — café</topicref></map>")
    assert tree.nodes["n.0"].content_properties["text"] == "Introducción — café"


def test_document_order_is_deterministic() -> None:
    xml = "<map><a/><b/><c/></map>"
    first = _adapt(xml)
    second = _adapt(xml)
    assert list(first.nodes) == list(second.nodes)
    assert [first.nodes[r].node_type for r in ("n.0", "n.1", "n.2")] == ["a", "b", "c"]
