"""Unit tests for the generic JSON document adapter."""

from __future__ import annotations

import pytest

from reconciliation.adapters.json.canonical_adapter import JsonDocumentAdapter
from reconciliation.adapters.json.errors import InputParseError, UnsafeJsonError
from reconciliation.adapters.json.parser import JsonSecurityLimits
from reconciliation.core.validation.tree_validator import validate_tree_result


def _adapt(data: str):
    return JsonDocumentAdapter().adapt_document(data, tree_id="t", document_uri="doc.json")


def test_json_adapter_produces_valid_canonical_tree() -> None:
    tree = _adapt('{"name": "Ada", "roles": ["admin", "editor"]}')

    assert validate_tree_result(tree).valid
    assert tree.metadata["format"] == "json"
    assert tree.nodes["n.0"].node_type == "data:object"
    assert tree.nodes["n.0.1.0"].node_type == "data:array"


def test_json_object_field_order_is_preserved_in_node_refs() -> None:
    first = _adapt('{"a": 1, "b": 2}')
    second = _adapt('{"b": 2, "a": 1}')

    assert first.nodes["n.0.0"].identity_properties["key"] == "a"
    assert second.nodes["n.0.0"].identity_properties["key"] == "b"


def test_malformed_json_is_rejected() -> None:
    with pytest.raises(InputParseError) as excinfo:
        _adapt('{"unclosed": ')
    assert excinfo.value.code == "INVALID_INPUT"


def test_json_limits_are_enforced() -> None:
    adapter = JsonDocumentAdapter(limits=JsonSecurityLimits(max_bytes=10, max_depth=3))

    with pytest.raises(UnsafeJsonError) as excinfo:
        adapter.adapt_document('{"too": "long"}', tree_id="t")
    assert excinfo.value.code == "UNSAFE_JSON"

    with pytest.raises(UnsafeJsonError):
        adapter.adapt_document('{"a": {"b": {"c": 1}}}', tree_id="t")


def test_non_finite_json_constants_are_rejected() -> None:
    with pytest.raises(InputParseError):
        _adapt('{"x": NaN}')
