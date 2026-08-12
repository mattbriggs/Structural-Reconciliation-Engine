"""The localization layer's guard against contradictory statuses (REQ-058, REQ-090).

The core already withholds presence operations for unresolved correspondences,
so this guard is the second barrier: it must hold even when the core is
explicitly told to force a total interpretation.
"""

from __future__ import annotations

from reconciliation.core.contracts.profiles import (
    OperationProfile,
    OperationType,
    UnresolvedPresencePolicy,
)
from reconciliation.core.contracts.tree import CanonicalTree
from tests.app_builders import localize, statuses
from tests.builders import TreeBuilder


def _repeated_siblings() -> tuple[CanonicalTree, CanonicalTree]:
    src = (
        TreeBuilder("s", "r", node_type="map")
        .child("r", "s1", node_type="item", content={"t": "x"})
        .child("r", "s2", node_type="item", content={"t": "x"})
        .build()
    )
    tgt = (
        TreeBuilder("t", "r", node_type="map")
        .child("r", "t1", node_type="item", content={"t": "x"})
        .child("r", "t2", node_type="item", content={"t": "x"})
        .build()
    )
    return src, tgt


def test_guard_holds_when_the_core_is_forced_to_emit_presence_operations() -> None:
    src, tgt = _repeated_siblings()
    forced = OperationProfile(
        profile_id="op-emit-all",
        version="v1",
        unresolved_presence_policy=UnresolvedPresencePolicy.EMIT_ALL,
    )
    result = localize(src, tgt, operation_profile=forced)

    # Ambiguity dominates: no missing/extra finding for an ambiguous node.
    assert set(statuses(result)) == {"AMBIGUOUS_MATCH"}
    # The core record is referenced unmodified, forced operations included
    # (REQ-176) — the layer filters its own interpretation, not the evidence.
    assert result.reconciliation.operations.of_type(OperationType.DELETE)
    assert result.reconciliation.operations.of_type(OperationType.INSERT)
    assert result.summary.unresolved_region_count == 1


def test_guard_keeps_presence_findings_for_unambiguous_nodes() -> None:
    src = (
        TreeBuilder("s", "r", node_type="map")
        .child("r", "a", identity={"id": "a"})
        .child("r", "b", identity={"id": "b"})
        .build()
    )
    tgt = TreeBuilder("t", "r", node_type="map").child("r", "a", identity={"id": "a"}).build()
    result = localize(src, tgt)

    assert "MISSING_IN_LOCALE" in statuses(result)
    assert result.summary.unresolved_region_count == 0
