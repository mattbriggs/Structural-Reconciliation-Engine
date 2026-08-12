"""Unit tests for the generic YAML document adapter."""

from __future__ import annotations

import pytest

from reconciliation.adapters.yaml.canonical_adapter import YamlDocumentAdapter
from reconciliation.adapters.yaml.errors import InputParseError, UnsafeYamlError
from reconciliation.adapters.yaml.parser import YamlSecurityLimits
from reconciliation.core.validation.tree_validator import validate_tree_result


def _adapt(data: str):
    return YamlDocumentAdapter().adapt_document(data, tree_id="t", document_uri="doc.yaml")


def test_yaml_adapter_produces_valid_canonical_tree() -> None:
    tree = _adapt("name: Ada\nroles:\n  - admin\n  - editor\n")

    assert validate_tree_result(tree).valid
    assert tree.metadata["format"] == "yaml"
    assert tree.nodes["n.0"].node_type == "data:object"
    assert tree.nodes["n.0.1.0"].node_type == "data:array"


def test_empty_yaml_document_maps_to_null() -> None:
    tree = _adapt("")

    assert tree.nodes["n.0"].node_type == "data:null"
    assert tree.nodes["n.0"].content_properties["value"] is None


def test_non_string_mapping_keys_are_rejected() -> None:
    with pytest.raises(UnsafeYamlError) as excinfo:
        _adapt("1: one\n")
    assert excinfo.value.code == "UNSAFE_YAML"


def test_unsupported_yaml_constructs_are_rejected() -> None:
    for document in (
        "base: &base\n  a: 1\ncopy: *base\n",
        "merged:\n  <<: {a: 1}\n",
        "value: !custom tagged\n",
        "---\na: 1\n---\nb: 2\n",
    ):
        with pytest.raises(UnsafeYamlError):
            _adapt(document)


def test_malformed_yaml_is_rejected() -> None:
    with pytest.raises(InputParseError) as excinfo:
        _adapt("a: [unclosed\n")
    assert excinfo.value.code == "INVALID_INPUT"


def test_yaml_limits_are_enforced() -> None:
    adapter = YamlDocumentAdapter(limits=YamlSecurityLimits(max_bytes=10, max_depth=3))

    with pytest.raises(UnsafeYamlError):
        adapter.adapt_document("name: too long\n", tree_id="t")
    with pytest.raises(UnsafeYamlError):
        adapter.adapt_document("a:\n  b:\n    c: 1\n", tree_id="t")
