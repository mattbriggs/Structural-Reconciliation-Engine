"""Unit tests for JSON/YAML data-tree canonicalization."""

from __future__ import annotations

from reconciliation.adapters.data_tree import DataTreeAdapter
from reconciliation.core.validation.tree_validator import validate_tree_result


def _adapt(value: object):
    return DataTreeAdapter(source_format="json").adapt(
        value,
        tree_id="t",
        document_uri="doc.json",
    )


def test_mapping_fields_become_deterministic_property_nodes() -> None:
    tree = _adapt({"name": "Ada", "active": True})

    assert validate_tree_result(tree).valid
    assert tree.nodes["n"].node_type == "data:document"
    assert tree.nodes["n.0"].node_type == "data:object"
    assert tree.nodes["n.0"].child_refs == ("n.0.0", "n.0.1")
    assert tree.nodes["n.0.0"].node_type == "data:property"
    assert tree.nodes["n.0.0"].identity_properties["key"] == "name"
    assert tree.nodes["n.0.0"].content_properties["value"] == "Ada"
    assert tree.nodes["n.0.1"].content_properties["value"] is True


def test_container_values_are_attached_as_child_nodes() -> None:
    tree = _adapt({"items": ["a", "b"]})

    prop = tree.nodes["n.0.0"]
    array = tree.nodes["n.0.0.0"]
    assert prop.child_refs == ("n.0.0.0",)
    assert array.node_type == "data:array"
    assert array.child_refs == ("n.0.0.0.0", "n.0.0.0.1")
    assert tree.nodes["n.0.0.0.1"].node_type == "data:item"
    assert tree.nodes["n.0.0.0.1"].content_properties["value"] == "b"


def test_root_scalar_is_a_leaf_value_node() -> None:
    tree = _adapt(None)

    assert tree.nodes["n"].child_refs == ("n.0",)
    assert tree.nodes["n.0"].node_type == "data:null"
    assert tree.nodes["n.0"].content_properties["value"] is None
