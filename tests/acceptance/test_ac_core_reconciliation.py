"""Acceptance tests AC-001 .. AC-012 (core reconciliation).

Each test maps to one SRS acceptance criterion so the acceptance matrix is
mechanically greppable (``grep test_ac_0``). Localization-status criteria that
require the application layer are covered separately.
"""

from __future__ import annotations

import pytest

from reconciliation.core.contracts.matches import MatchState
from reconciliation.core.contracts.profiles import (
    AlignmentProfile,
    AlignmentStrategy,
    OperationType,
    OrderSemantics,
)
from tests.builders import TreeBuilder, operation_types, reconcile

pytestmark = pytest.mark.acceptance


def test_ac_001_identical_trees() -> None:
    src = TreeBuilder("s", "r", node_type="map").child("r", "a", identity={"id": "a"}).child(
        "r", "b", identity={"id": "b"}
    ).build()
    tgt = TreeBuilder("t", "r", node_type="map").child("r", "a", identity={"id": "a"}).child(
        "r", "b", identity={"id": "b"}
    ).build()
    result = reconcile(src, tgt)
    assert set(operation_types(result)) == {"MATCH"}
    assert all(op.type is OperationType.MATCH for op in result.operations.operations)


def test_ac_002_inserted_sibling_does_not_cascade() -> None:
    src = TreeBuilder("s", "r", node_type="map").child("r", "a", identity={"id": "a"}).child(
        "r", "b", identity={"id": "b"}
    ).build()
    tgt = (
        TreeBuilder("t", "r", node_type="map")
        .child("r", "a", identity={"id": "a"})
        .child("r", "x", identity={"id": "x"})
        .child("r", "b", identity={"id": "b"})
        .build()
    )
    result = reconcile(src, tgt)
    inserts = result.operations.of_type(OperationType.INSERT)
    assert len(inserts) == 1
    assert inserts[0].target_node_refs == ("x",)
    # 'b' remains matched, not reported as a mismatch cascade.
    assert result.match_graph.confirmed_target_for("b") == "b"


def test_ac_004_simple_subtree_move_suppresses_descendants() -> None:
    src = (
        TreeBuilder("s", "r", node_type="map")
        .child("r", "p1", identity={"id": "p1"})
        .child("r", "p2", identity={"id": "p2"})
        .child("p1", "a", identity={"id": "a"})
        .child("a", "a1", identity={"id": "a1"})
        .build()
    )
    tgt = (
        TreeBuilder("t", "r", node_type="map")
        .child("r", "p1", identity={"id": "p1"})
        .child("r", "p2", identity={"id": "p2"})
        .child("p2", "a", identity={"id": "a"})
        .child("a", "a1", identity={"id": "a1"})
        .build()
    )
    result = reconcile(src, tgt)
    moves = result.operations.of_type(OperationType.MOVE)
    assert len(moves) == 1
    assert moves[0].source_node_refs == ("a",)
    # Descendant path change is suppressed, not reported as a defect.
    categories = [e.category for e in result.suppression.suppressed_effects]
    assert "DESCENDANT_PATH_CHANGED" in categories


def test_ac_005_insufficient_move_confidence_falls_back() -> None:
    # No stable ids: moved subtree has only moderate similarity evidence, below
    # the move threshold, so no high-confidence MOVE is emitted.
    src = (
        TreeBuilder("s", "r", node_type="map")
        .child("r", "p1", identity={"id": "p1"})
        .child("r", "p2", identity={"id": "p2"})
        .child("p1", "a", node_type="item", content={"t": "alpha"})
        .build()
    )
    tgt = (
        TreeBuilder("t", "r", node_type="map")
        .child("r", "p1", identity={"id": "p1"})
        .child("r", "p2", identity={"id": "p2"})
        .child("p2", "b", node_type="item", content={"t": "beta"})
        .build()
    )
    result = reconcile(src, tgt)
    # Evidence is too weak to confirm identity across parents, so no
    # high-confidence MOVE is asserted (it degrades to delete + insert).
    assert not result.operations.of_type(OperationType.MOVE)


def test_ac_006_sibling_reorder() -> None:
    src = TreeBuilder("s", "r", node_type="map").child("r", "a", identity={"id": "a"}).child(
        "r", "b", identity={"id": "b"}
    ).build()
    tgt = TreeBuilder("t", "r", node_type="map").child("r", "b", identity={"id": "b"}).child(
        "r", "a", identity={"id": "a"}
    ).build()
    result = reconcile(src, tgt)
    reorders = result.operations.of_type(OperationType.REORDER)
    assert len(reorders) == 1
    assert set(reorders[0].source_node_refs) == {"a", "b"}
    assert not result.operations.of_type(OperationType.MOVE)


def test_ac_007_order_insensitive_collection() -> None:
    src = TreeBuilder("s", "r", node_type="map").child("r", "a", identity={"id": "a"}).child(
        "r", "b", identity={"id": "b"}
    ).build()
    tgt = TreeBuilder("t", "r", node_type="map").child("r", "b", identity={"id": "b"}).child(
        "r", "a", identity={"id": "a"}
    ).build()
    unordered = AlignmentProfile(
        profile_id="align-unordered",
        version="v1",
        strategy=AlignmentStrategy.LCS,
        default_order_semantics=OrderSemantics.UNORDERED,
    )
    result = reconcile(src, tgt, alignment_profile=unordered)
    assert not result.operations.of_type(OperationType.REORDER)


def test_ac_008_content_update_without_identity_loss() -> None:
    src = TreeBuilder("s", "r", node_type="map").child(
        "r", "a", identity={"id": "a"}, content={"title": "Hello"}
    ).build()
    tgt = TreeBuilder("t", "r", node_type="map").child(
        "r", "a", identity={"id": "a"}, content={"title": "Bonjour"}
    ).build()
    result = reconcile(src, tgt)
    assert result.operations.of_type(OperationType.UPDATE)
    assert not result.operations.of_type(OperationType.DELETE)
    assert not result.operations.of_type(OperationType.INSERT)
    assert result.match_graph.confirmed_target_for("a") == "a"


def test_ac_009_repeated_ambiguous_structure_not_forced_by_position() -> None:
    src = TreeBuilder("s", "r", node_type="map").child(
        "r", "s1", node_type="item", content={"t": "x"}
    ).child("r", "s2", node_type="item", content={"t": "x"}).build()
    tgt = TreeBuilder("t", "r", node_type="map").child(
        "r", "t1", node_type="item", content={"t": "x"}
    ).child("r", "t2", node_type="item", content={"t": "x"}).build()
    result = reconcile(src, tgt)
    # No item is confirmed to a specific position; alternatives are preserved.
    item_confirmed = [
        c for c in result.match_graph.confirmed if c.source_node_ref in {"s1", "s2"}
    ]
    assert item_confirmed == []
    assert len(result.match_graph.ambiguous) >= 2
    for c in result.match_graph.ambiguous:
        assert c.alternative_match_ids


def test_ac_010_duplicate_persistent_id_reported() -> None:
    src = TreeBuilder("s", "r", node_type="map").child(
        "r", "a", identity={"id": "dup"}
    ).child("r", "b", identity={"id": "dup"}).build()
    tgt = TreeBuilder("t", "r", node_type="map").child(
        "r", "c", identity={"id": "dup"}
    ).build()
    result = reconcile(src, tgt)
    assert any(d.code == "DUPLICATE_PERSISTENT_ID" for d in result.diagnostics)
    # Duplicate id is not used as authoritative identity.
    for c in result.match_graph.confirmed:
        assert not (c.source_node_ref in {"a", "b"} and c.confidence.value == 1.0)


def test_ac_011_contradictory_id_and_type_rejected() -> None:
    # Same id on incompatible node types -> hard constraint rejects the match.
    src = TreeBuilder("s", "r", node_type="map").child(
        "r", "a", node_type="topicref", identity={"id": "shared"}
    ).build()
    tgt = TreeBuilder("t", "r", node_type="map").child(
        "r", "b", node_type="keydef", identity={"id": "shared"}
    ).build()
    result = reconcile(src, tgt)
    rejected = [c for c in result.match_graph.candidates if c.state is MatchState.REJECTED]
    assert rejected
    assert result.match_graph.confirmed_target_for("a") is None


def test_ac_012_deterministic_output() -> None:
    src = (
        TreeBuilder("s", "r", node_type="map")
        .child("r", "a", identity={"id": "a"})
        .child("r", "b", identity={"id": "b"})
        .child("a", "a1", identity={"id": "a1"})
        .build()
    )
    tgt = (
        TreeBuilder("t", "r", node_type="map")
        .child("r", "b", identity={"id": "b"})
        .child("r", "a", identity={"id": "a"})
        .child("a", "a1", identity={"id": "a1"})
        .build()
    )
    first = reconcile(src, tgt).deterministic_fingerprint()
    second = reconcile(src, tgt).deterministic_fingerprint()
    assert first == second
