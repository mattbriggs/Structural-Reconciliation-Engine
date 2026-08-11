"""Acceptance tests AC-013 .. AC-015 (suppression safety)."""

from __future__ import annotations

import pytest

from reconciliation.core.contracts.profiles import (
    OperationProfile,
    OperationType,
    SuppressionProfile,
    SuppressionRule,
)
from reconciliation.core.contracts.suppression import IndependentDefectCheck
from tests.builders import TreeBuilder, reconcile

pytestmark = pytest.mark.acceptance


def _moved_subtree(defect: bool) -> tuple:
    """Source p1>a>a1; target p2>a>a1. ``defect`` changes a1's content."""
    src = (
        TreeBuilder("s", "r", node_type="map")
        .child("r", "p1", identity={"id": "p1"})
        .child("r", "p2", identity={"id": "p2"})
        .child("p1", "a", identity={"id": "a"})
        .child("a", "a1", identity={"id": "a1"}, content={"t": "orig"})
        .build()
    )
    tgt = (
        TreeBuilder("t", "r", node_type="map")
        .child("r", "p1", identity={"id": "p1"})
        .child("r", "p2", identity={"id": "p2"})
        .child("p2", "a", identity={"id": "a"})
        .child("a", "a1", identity={"id": "a1"}, content={"t": "changed" if defect else "orig"})
        .build()
    )
    return src, tgt


def test_ac_013_transparent_suppression() -> None:
    src, tgt = _moved_subtree(defect=False)
    result = reconcile(src, tgt)
    effects = result.suppression.suppressed_effects
    assert effects
    operation_ids = {op.operation_id for op in result.operations.operations}
    for effect in effects:
        # Each suppressed effect remains available and references its root
        # operation and suppression rule.
        assert effect.root_operation_id in operation_ids
        assert effect.suppression_rule_id
        assert effect.independent_defect_check is IndependentDefectCheck.PASSED


def test_ac_014_independent_downstream_defect_retained() -> None:
    src, tgt = _moved_subtree(defect=True)
    result = reconcile(src, tgt)
    # Move is detected and descendant path change suppressed...
    assert result.operations.of_type(OperationType.MOVE)
    assert any(
        e.category == "DESCENDANT_PATH_CHANGED" for e in result.suppression.suppressed_effects
    )
    # ...but the independent content defect on a1 is retained and still visible.
    assert "a1" in result.suppression.retained_defect_node_refs
    updates = result.operations.of_type(OperationType.UPDATE)
    assert any("a1" in op.source_node_refs for op in updates)


def test_ac_015_low_confidence_root_operation_not_suppressed() -> None:
    # A non-authoritative (id-less) move with only partial evidence yields a
    # MOVE with fractional confidence. With the suppression threshold set above
    # that confidence, dependent effects must NOT be suppressed as fact.
    src = (
        TreeBuilder("s", "r", node_type="map")
        .child("r", "p1", identity={"id": "p1"})
        .child("r", "p2", identity={"id": "p2"})
        .child("p1", "a", node_type="item", content={"t": "x"})
        .child("a", "a1", node_type="leaf")  # child present in source only
        .build()
    )
    tgt = (
        TreeBuilder("t", "r", node_type="map")
        .child("r", "p1", identity={"id": "p1"})
        .child("r", "p2", identity={"id": "p2"})
        .child("p2", "a", node_type="item", content={"t": "x"})  # no child => partial evidence
        .build()
    )
    op_profile = OperationProfile(
        profile_id="op-lowmove", version="v1", move_confidence_threshold=0.3
    )
    strict_suppression = SuppressionProfile(
        profile_id="s-high",
        version="v1",
        rules=(
            SuppressionRule(
                rule_id="move-descendant-path-strict",
                root_operation=OperationType.MOVE,
                effect_category="DESCENDANT_PATH_CHANGED",
                threshold=0.99,
            ),
        ),
    )
    from reconciliation.core.contracts.commands import ExecutionContext, ReconcileTreesCommand
    from reconciliation.core.engine import DefaultReconciliationEngine
    from tests.builders import (
        default_alignment_profile,
        default_matching_profile,
        default_normalization_profile,
    )

    command = ReconcileTreesCommand(
        source_tree=src,
        target_tree=tgt,
        normalization_profile=default_normalization_profile(),
        matching_profile=default_matching_profile(),
        alignment_profile=default_alignment_profile(),
        operation_profile=op_profile,
        suppression_profile=strict_suppression,
        execution_context=ExecutionContext(job_id="job"),
    )
    result = DefaultReconciliationEngine().reconcile(command)
    moves = result.operations.of_type(OperationType.MOVE)
    assert moves and moves[0].confidence.value < 0.99
    # Below the suppression threshold: nothing is suppressed (AC-015).
    assert result.suppression.suppressed_effects == ()
