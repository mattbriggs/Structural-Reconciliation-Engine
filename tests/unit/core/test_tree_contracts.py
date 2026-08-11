"""Unit tests for canonical tree contracts and validation (REQ-165-170)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from reconciliation.core.contracts.tree import CanonicalNode, CanonicalTree, SourceLocation
from reconciliation.core.errors import InvalidTreeError
from reconciliation.core.validation.tree_validator import validate_tree, validate_tree_result
from tests.builders import TreeBuilder


def _tree_with(nodes: dict[str, CanonicalNode], root: str = "root") -> CanonicalTree:
    return CanonicalTree(
        contract_version="canonical-tree-v1", tree_id="t", root_node_ref=root, nodes=nodes
    )


def test_valid_tree_passes_all_invariants() -> None:
    tree = (
        TreeBuilder("t", "root")
        .child("root", "a")
        .child("root", "b")
        .child("a", "a1")
        .build()
    )
    result = validate_tree_result(tree)
    assert result.valid
    assert result.violations == ()


def test_source_location_rejects_nonpositive_line() -> None:
    with pytest.raises(ValidationError):
        SourceLocation(line=0)


def test_node_rejects_duplicate_children() -> None:
    # REQ-168: a node must not list the same child twice.
    with pytest.raises(ValidationError):
        CanonicalNode(node_ref="p", node_type="x", child_refs=("c", "c"))


def test_node_cannot_be_its_own_parent() -> None:
    with pytest.raises(ValidationError):
        CanonicalNode(node_ref="n", node_type="x", parent_ref="n")


def test_tree_requires_root_present() -> None:
    # REQ-169 root must resolve.
    node = CanonicalNode(node_ref="a", node_type="x")
    with pytest.raises(ValidationError):
        _tree_with({"a": node}, root="missing")


def test_root_must_have_no_parent() -> None:
    # REQ-169
    with pytest.raises(ValidationError):
        _tree_with(
            {
                "root": CanonicalNode(node_ref="root", node_type="x", parent_ref="ghost"),
            }
        )


def test_dangling_child_reference_detected() -> None:
    # REQ-166
    tree = _tree_with(
        {"root": CanonicalNode(node_ref="root", node_type="x", child_refs=("gone",))}
    )
    result = validate_tree_result(tree)
    assert not result.valid
    assert any(v.code == "DANGLING_CHILD_REF" for v in result.violations)


def test_parent_child_disagreement_detected() -> None:
    tree = _tree_with(
        {
            "root": CanonicalNode(node_ref="root", node_type="x", child_refs=("a",)),
            # 'a' claims a different parent than the one listing it as a child.
            "a": CanonicalNode(node_ref="a", node_type="x", parent_ref="root", child_refs=()),
            "b": CanonicalNode(node_ref="b", node_type="x", parent_ref="root"),
        }
    )
    # 'b' points to root as parent but root does not list b as a child.
    result = validate_tree_result(tree)
    assert not result.valid
    assert any(v.code == "MISSING_FROM_PARENT_CHILDREN" for v in result.violations)


def test_multiple_roots_detected() -> None:
    tree = _tree_with(
        {
            "root": CanonicalNode(node_ref="root", node_type="x", child_refs=("a",)),
            "a": CanonicalNode(node_ref="a", node_type="x", parent_ref="root"),
            "orphan": CanonicalNode(node_ref="orphan", node_type="x"),
        }
    )
    result = validate_tree_result(tree)
    assert not result.valid
    assert any(v.code == "MULTIPLE_ROOTS" for v in result.violations)


def test_containment_cycle_detected() -> None:
    # REQ-170: build a cycle a -> b -> a bypassing model-level self checks.
    tree = _tree_with(
        {
            "root": CanonicalNode(node_ref="root", node_type="x", child_refs=("a",)),
            "a": CanonicalNode(node_ref="a", node_type="x", parent_ref="b", child_refs=("b",)),
            "b": CanonicalNode(node_ref="b", node_type="x", parent_ref="a", child_refs=("a",)),
        },
    )
    result = validate_tree_result(tree)
    assert not result.valid
    assert any(v.code == "CONTAINMENT_CYCLE" for v in result.violations)


def test_validate_tree_raises_invalid_tree_error() -> None:
    tree = _tree_with(
        {"root": CanonicalNode(node_ref="root", node_type="x", child_refs=("gone",))}
    )
    with pytest.raises(InvalidTreeError) as exc:
        validate_tree(tree, correlation_id="corr-1")
    assert exc.value.code == "INVALID_TREE"
    assert exc.value.correlation_id == "corr-1"
    assert exc.value.retryable is False
