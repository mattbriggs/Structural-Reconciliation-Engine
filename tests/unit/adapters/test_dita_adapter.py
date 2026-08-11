"""Unit tests for the DITA map adapter (REQ-033, REQ-034, REQ-113)."""

from __future__ import annotations

from reconciliation.adapters.dita.identity import extract_identity, extract_navtitle
from reconciliation.adapters.dita.map_adapter import DitaMapAdapter
from reconciliation.adapters.dita.normalization import normalize_href, normalize_keys
from reconciliation.adapters.xml.parser import SecureXmlParser
from reconciliation.core.validation.tree_validator import validate_tree_result


def _adapt(xml: str):
    return DitaMapAdapter().adapt_document(xml, tree_id="t", document_uri="m.ditamap")


def test_normalize_href_strips_leading_dot_slash() -> None:
    assert normalize_href("./topics/intro.dita#x") == "topics/intro.dita#x"


def test_normalize_keys_splits_and_orders() -> None:
    assert normalize_keys("  intro  setup ") == ("intro", "setup")


def test_canonical_id_prefers_id_then_keys_then_href() -> None:
    tree = _adapt(
        "<map>"
        "<topicref id='explicit' keys='k' href='h.dita'/>"
        "<topicref keys='mykey' href='h2.dita'/>"
        "<topicref href='h3.dita'/>"
        "</map>"
    )
    assert tree.nodes["n.0"].identity_properties["id"] == "explicit"
    assert tree.nodes["n.1"].identity_properties["id"] == "keys:mykey"
    assert tree.nodes["n.2"].identity_properties["id"] == "href:h3.dita"


def test_navtitle_from_attribute_and_topicmeta() -> None:
    attr = "<topicref navtitle='Attr Title'/>"
    from lxml import etree

    assert extract_navtitle(etree.fromstring(attr)) == "Attr Title"
    meta = "<topicref><topicmeta><navtitle>Meta Title</navtitle></topicmeta></topicref>"
    assert extract_navtitle(etree.fromstring(meta)) == "Meta Title"


def test_navtitle_mapped_to_content_and_topicmeta_folded() -> None:
    tree = _adapt(
        "<map><topicref keys='a'><topicmeta><navtitle>Intro</navtitle></topicmeta></topicref></map>"
    )
    node = tree.nodes["n.0"]
    assert node.content_properties["navtitle"] == "Intro"
    # topicmeta is folded into the parent, not emitted as a child node.
    assert node.child_refs == ()
    assert validate_tree_result(tree).valid


def test_keys_and_href_retained_for_audit() -> None:
    tree = _adapt("<map><topicref keys='intro' href='./intro.dita'/></map>")
    node = tree.nodes["n.0"]
    assert node.identity_properties["keys"] == "intro"
    assert node.identity_properties["href"] == "intro.dita"


def test_extract_identity_direct() -> None:
    from lxml import etree

    element = etree.fromstring("<topicref id='a' keys='k1 k2' href='./t.dita'/>")
    identity = extract_identity(element)
    assert identity == {"id": "a", "keys": "k1 k2", "href": "t.dita"}


def test_dita_document_is_parsed_securely() -> None:
    # A DITA-style DOCTYPE is allowed, but its external DTD is never fetched.
    doc = (
        '<?xml version="1.0"?>'
        '<!DOCTYPE map PUBLIC "-//OASIS//DTD DITA Map//EN" "map.dtd">'
        "<map><topicref keys='a'/></map>"
    )
    root = SecureXmlParser().parse(doc)
    assert root.tag == "map"
