"""Unit tests for the unresolved-alignment contracts and policies (REQ-058).

Covers the invariants that keep "unresolved" from decaying back into "absent",
and the two explicit escape hatches on :class:`OperationProfile` so the profile
surface is backed by real behavior.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from reconciliation.core.contracts.alignment import (
    AlignedPair,
    AlignedRegion,
    AlignmentEdgeKind,
    AlignmentResult,
)
from reconciliation.core.contracts.profiles import (
    AlignmentProfile,
    AlignmentStrategy,
    OperationProfile,
    OperationType,
    UnresolvedPresencePolicy,
)
from reconciliation.core.contracts.tree import CanonicalTree
from tests.builders import TreeBuilder, reconcile


def _unresolved_pair() -> AlignedPair:
    return AlignedPair(
        kind=AlignmentEdgeKind.UNRESOLVED_SOURCE,
        source_node_ref="s1",
        ambiguous_match_ids=("m:s1->t1", "m:s1->t2"),
    )


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


# -- Contract invariants ---------------------------------------------------


def test_unresolved_pair_requires_candidate_match_ids() -> None:
    with pytest.raises(ValidationError, match="ambiguous candidate match"):
        AlignedPair(kind=AlignmentEdgeKind.UNRESOLVED_TARGET, target_node_ref="t1")


def test_aligned_pair_requires_both_endpoints() -> None:
    with pytest.raises(ValidationError, match="both a source and a target"):
        AlignedPair(kind=AlignmentEdgeKind.ALIGNED, source_node_ref="s1")


def test_region_holding_unresolved_positions_must_be_marked_unresolved() -> None:
    with pytest.raises(ValidationError, match="must be marked unresolved"):
        AlignedRegion(region_id="region:r->r", pairs=(_unresolved_pair(),))


def test_result_unresolved_ids_must_match_marked_regions() -> None:
    region = AlignedRegion(
        region_id="region:r->r", pairs=(_unresolved_pair(),), unresolved=True
    )
    with pytest.raises(ValidationError, match="must list exactly the unresolved regions"):
        AlignmentResult(regions=(region,))
    with pytest.raises(ValidationError, match="must list exactly the unresolved regions"):
        AlignmentResult(regions=(region,), unresolved_region_ids=("region:other",))

    result = AlignmentResult(regions=(region,), unresolved_region_ids=(region.region_id,))
    assert result.unresolved_regions == (region,)
    assert result.region_by_id("region:r->r") is region
    assert result.region_by_id("nope") is None


def test_region_ids_must_be_unique() -> None:
    region = AlignedRegion(region_id="region:r->r")
    with pytest.raises(ValidationError, match="region ids must be unique"):
        AlignmentResult(regions=(region, region))


# -- Presence policies -----------------------------------------------------


def test_default_policy_suppresses_only_ambiguous_nodes() -> None:
    assert (
        OperationProfile(profile_id="p", version="v1").unresolved_presence_policy
        is UnresolvedPresencePolicy.SUPPRESS_AMBIGUOUS_NODES
    )


def test_emit_all_policy_forces_presence_operations_and_says_so() -> None:
    src, tgt = _repeated_siblings()
    profile = OperationProfile(
        profile_id="op-emit-all",
        version="v1",
        unresolved_presence_policy=UnresolvedPresencePolicy.EMIT_ALL,
    )
    result = reconcile(src, tgt, operation_profile=profile)

    assert len(result.operations.of_type(OperationType.DELETE)) == 2
    assert len(result.operations.of_type(OperationType.INSERT)) == 2
    # The forced conclusion is labeled as forced, not as clean one-sided evidence.
    for op in result.operations.operations:
        if op.type in (OperationType.DELETE, OperationType.INSERT):
            assert "UNRESOLVED_CORRESPONDENCE_FORCED_BY_POLICY" in op.evidence_codes
    # The alignment still records the ambiguity honestly.
    assert result.alignment.unresolved_region_ids


def test_suppress_unresolved_regions_policy_withholds_the_whole_region() -> None:
    # A real extra node beside an ambiguity: reported by default, withheld under
    # the maximally cautious policy.
    src = (
        TreeBuilder("s", "r", node_type="map")
        .child("r", "i1", node_type="item", content={"t": "x"})
        .child("r", "i2", node_type="item", content={"t": "x"})
        .build()
    )
    tgt = (
        TreeBuilder("t", "r", node_type="map")
        .child("r", "j1", node_type="item", content={"t": "x"})
        .child("r", "j2", node_type="item", content={"t": "x"})
        .child("r", "extra", node_type="topicref", identity={"id": "extra"})
        .build()
    )
    default = reconcile(src, tgt)
    assert [op.target_node_refs for op in default.operations.of_type(OperationType.INSERT)] == [
        ("extra",)
    ]

    cautious = reconcile(
        src,
        tgt,
        operation_profile=OperationProfile(
            profile_id="op-cautious",
            version="v1",
            unresolved_presence_policy=(
                UnresolvedPresencePolicy.SUPPRESS_UNRESOLVED_REGIONS
            ),
        ),
    )
    assert not cautious.operations.of_type(OperationType.INSERT)
    assert cautious.alignment.unresolved_region_ids == ("region:r->r",)


# -- Unhonored capabilities are reported, not silently ignored -------------


def test_unimplemented_alignment_strategy_is_reported() -> None:
    src = TreeBuilder("s", "r", node_type="map").child("r", "a", identity={"id": "a"}).build()
    tgt = TreeBuilder("t", "r", node_type="map").child("r", "a", identity={"id": "a"}).build()
    result = reconcile(
        src,
        tgt,
        alignment_profile=AlignmentProfile(
            profile_id="align-dp", version="v1", strategy=AlignmentStrategy.WEIGHTED_DP
        ),
    )
    diagnostic = next(
        d for d in result.diagnostics if d.code == "ALIGNMENT_STRATEGY_NOT_IMPLEMENTED"
    )
    assert diagnostic.metadata["requested_strategy"] == "WEIGHTED_DP"
    assert diagnostic.metadata["applied_strategy"] == "LCS"


def test_lcs_strategy_emits_no_strategy_diagnostic() -> None:
    src = TreeBuilder("s", "r", node_type="map").child("r", "a", identity={"id": "a"}).build()
    tgt = TreeBuilder("t", "r", node_type="map").child("r", "a", identity={"id": "a"}).build()
    result = reconcile(src, tgt)
    assert not [
        d for d in result.diagnostics if d.code == "ALIGNMENT_STRATEGY_NOT_IMPLEMENTED"
    ]
