"""Property-based invariant tests (REQ-202, REQ-255, REQ-260, REQ-264).

Generates random rooted trees and asserts the engine's cross-cutting
invariants hold: deterministic output, one-to-one confirmed matches, operation
references resolve, and every suppressed effect references a real operation and
never deletes it.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from reconciliation.core.contracts.matches import MatchState
from reconciliation.core.contracts.tree import CanonicalTree
from tests.builders import TreeBuilder, reconcile

pytestmark = pytest.mark.property


@st.composite
def random_tree(draw: st.DrawFn) -> CanonicalTree:
    """Generate a small rooted tree with unique per-node ids."""
    size = draw(st.integers(min_value=1, max_value=8))
    builder = TreeBuilder("tree", "n0", node_type="map")
    for i in range(1, size):
        parent = draw(st.integers(min_value=0, max_value=i - 1))
        builder.child(f"n{parent}", f"n{i}", node_type="item", identity={"id": f"id-{i}"})
    return builder.build()


@settings(max_examples=60, deadline=None)
@given(tree=random_tree())
def test_self_reconciliation_is_all_match_and_deterministic(tree: CanonicalTree) -> None:
    first = reconcile(tree, tree)
    second = reconcile(tree, tree)
    # Determinism (AC-012).
    assert first.deterministic_fingerprint() == second.deterministic_fingerprint()
    # No spurious insert/delete/move for a tree compared with itself.
    types = {op.type.value for op in first.operations.operations}
    assert types <= {"MATCH"}


@settings(max_examples=60, deadline=None)
@given(tree=random_tree())
def test_confirmed_matches_are_one_to_one(tree: CanonicalTree) -> None:
    result = reconcile(tree, tree)
    sources = [c.source_node_ref for c in result.match_graph.confirmed]
    targets = [c.target_node_ref for c in result.match_graph.confirmed]
    assert len(sources) == len(set(sources))
    assert len(targets) == len(set(targets))


@settings(max_examples=60, deadline=None)
@given(source=random_tree(), target=random_tree())
def test_operation_and_suppression_references_resolve(
    source: CanonicalTree, target: CanonicalTree
) -> None:
    result = reconcile(source, target)
    source_refs = set(source.nodes)
    target_refs = set(target.nodes)
    for op in result.operations.operations:
        assert set(op.source_node_refs) <= source_refs
        assert set(op.target_node_refs) <= target_refs
        assert 0.0 <= op.confidence.value <= 1.0
    operation_ids = {op.operation_id for op in result.operations.operations}
    for effect in result.suppression.suppressed_effects:
        # Every suppressed effect references a real root operation (REQ-264)
        # and the operation is retained, not deleted (REQ-267).
        assert effect.root_operation_id in operation_ids


@settings(max_examples=40, deadline=None)
@given(source=random_tree(), target=random_tree())
def test_confirmed_matches_carry_evidence(
    source: CanonicalTree, target: CanonicalTree
) -> None:
    result = reconcile(source, target)
    for c in result.match_graph.candidates:
        if c.state in (MatchState.CONFIRMED, MatchState.AMBIGUOUS):
            assert c.evidence  # REQ-257


@settings(max_examples=50, deadline=None)
@given(tree=random_tree())
def test_node_map_iteration_order_does_not_affect_output(tree: CanonicalTree) -> None:
    # REQ-203: results must not depend on node-map iteration order.
    reversed_nodes = dict(reversed(list(tree.nodes.items())))
    shuffled = tree.model_copy(update={"nodes": reversed_nodes})
    assert (
        reconcile(tree, tree).deterministic_fingerprint()
        == reconcile(shuffled, shuffled).deterministic_fingerprint()
    )
