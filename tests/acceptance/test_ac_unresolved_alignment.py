"""Acceptance tests for unresolved alignment (REQ-058, REQ-071, REQ-090).

``DELETE``/``INSERT`` — and therefore ``MISSING_IN_LOCALE``/``EXTRA_IN_LOCALE``
— mean "no viable correspondence exists". A node held in ambiguous candidates
has a viable correspondence that is merely not uniquely resolvable, so the
engine must report *uncertainty*, not absence. These tests pin that distinction
against the regression it replaces: ambiguous repeated siblings degrading into
missing + extra findings on top of the ambiguity finding.
"""

from __future__ import annotations

import pytest

from reconciliation.core.contracts.alignment import AlignmentEdgeKind
from reconciliation.core.contracts.diagnostics import Severity
from reconciliation.core.contracts.profiles import OperationType
from reconciliation.core.contracts.tree import CanonicalTree
from tests.app_builders import localize, statuses
from tests.builders import TreeBuilder, reconcile

pytestmark = pytest.mark.acceptance


def _repeated_siblings() -> tuple[CanonicalTree, CanonicalTree]:
    """Two structurally identical siblings per side, with no stable ids."""
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


# -- A. Repeated sibling ambiguity does not degrade to missing/extra --------


def test_repeated_sibling_ambiguity_emits_no_presence_operations() -> None:
    src, tgt = _repeated_siblings()
    result = reconcile(src, tgt)

    assert result.match_graph.ambiguous
    assert not result.operations.of_type(OperationType.DELETE)
    assert not result.operations.of_type(OperationType.INSERT)


def test_repeated_sibling_ambiguity_is_recorded_as_unresolved_alignment() -> None:
    src, tgt = _repeated_siblings()
    result = reconcile(src, tgt)

    region = result.alignment.region_for("r", "r")
    assert region is not None
    assert region.unresolved
    assert result.alignment.unresolved_region_ids == (region.region_id,)
    # Positions record ambiguity, not absence, and name the competing candidates.
    kinds = {pair.kind for pair in region.pairs}
    assert kinds == {
        AlignmentEdgeKind.UNRESOLVED_SOURCE,
        AlignmentEdgeKind.UNRESOLVED_TARGET,
    }
    assert all(pair.ambiguous_match_ids for pair in region.pairs)
    assert result.alignment.unresolved_source_refs == frozenset({"s1", "s2"})
    assert result.alignment.unresolved_target_refs == frozenset({"t1", "t2"})
    assert any(d.code == "UNRESOLVED_ALIGNMENT_REGION" for d in result.diagnostics)


def test_repeated_sibling_ambiguity_reports_only_ambiguity_in_localization() -> None:
    src, tgt = _repeated_siblings()
    result = localize(src, tgt)

    present = set(statuses(result))
    assert present == {"AMBIGUOUS_MATCH"}
    assert "MISSING_IN_LOCALE" not in present
    assert "EXTRA_IN_LOCALE" not in present
    assert result.summary.unresolved_region_count == 1
    # Uncertainty is reported as a warning, never escalated to a hard defect.
    assert all(issue.severity is Severity.WARNING for issue in result.issues)


def test_ambiguity_cascade_regression_produces_one_finding_per_ambiguous_node() -> None:
    """Regression for the original cascade-noise problem.

    Before unresolved alignment existed, this pair produced two ambiguity
    findings *plus* two missing and two extra findings — six findings for one
    unresolved situation. It must now produce only the ambiguity findings.
    """
    src, tgt = _repeated_siblings()
    result = localize(src, tgt)

    assert len(result.issues) == 2
    assert result.summary.node_counts.ambiguous == 2
    assert result.summary.node_counts.missing == 0
    assert result.summary.node_counts.extra == 0
    # No recommendation is manufactured for an unresolved situation (AC-038).
    assert not result.recommendations


# -- B. Mixed region: one true insert beside one ambiguous pair -------------


def _mixed_region() -> tuple[CanonicalTree, CanonicalTree]:
    src = (
        TreeBuilder("s", "r", node_type="map")
        .child("r", "a", identity={"id": "a"})
        .child("r", "i1", node_type="item", content={"t": "x"})
        .child("r", "i2", node_type="item", content={"t": "x"})
        .build()
    )
    tgt = (
        TreeBuilder("t", "r", node_type="map")
        .child("r", "a", identity={"id": "a"})
        .child("r", "j1", node_type="item", content={"t": "x"})
        .child("r", "j2", node_type="item", content={"t": "x"})
        .child("r", "extra", node_type="topicref", identity={"id": "extra"})
        .build()
    )
    return src, tgt


def test_ambiguity_does_not_swallow_a_real_extra_node() -> None:
    src, tgt = _mixed_region()
    result = reconcile(src, tgt)

    inserts = result.operations.of_type(OperationType.INSERT)
    assert [op.target_node_refs for op in inserts] == [("extra",)]
    assert not result.operations.of_type(OperationType.DELETE)
    # The ambiguous pair stays ambiguous in the same region as the real defect.
    region = result.alignment.region_for("r", "r")
    assert region is not None
    assert region.unresolved
    assert region.unresolved_source_refs == ("i1", "i2")
    assert region.unresolved_target_refs == ("j1", "j2")
    assert any(
        pair.kind is AlignmentEdgeKind.TARGET_ONLY and pair.target_node_ref == "extra"
        for pair in region.pairs
    )


def test_mixed_region_reports_the_real_defect_and_the_ambiguity() -> None:
    src, tgt = _mixed_region()
    result = localize(src, tgt)

    present = statuses(result)
    assert present.count("EXTRA_IN_LOCALE") == 1
    assert present.count("AMBIGUOUS_MATCH") == 2
    assert "MISSING_IN_LOCALE" not in present
    extra = next(i for i in result.issues if i.localization_status.value == "EXTRA_IN_LOCALE")
    assert extra.locale_node_id == "extra"


# -- C. Ambiguous moved-like structure stays unresolved --------------------


def test_ambiguous_cross_parent_structure_stays_unresolved() -> None:
    # A repeated structure appears under a different parent in the target. The
    # evidence cannot say which node went where, so no MOVE may be asserted —
    # and neither may the DELETE + INSERT pair that a forced interpretation
    # would produce.
    src = (
        TreeBuilder("s", "r", node_type="map")
        .child("r", "p1", identity={"id": "p1"})
        .child("r", "p2", identity={"id": "p2"})
        .child("p1", "i1", node_type="item", content={"t": "x"})
        .child("p1", "i2", node_type="item", content={"t": "x"})
        .build()
    )
    tgt = (
        TreeBuilder("t", "r", node_type="map")
        .child("r", "p1", identity={"id": "p1"})
        .child("r", "p2", identity={"id": "p2"})
        .child("p2", "j1", node_type="item", content={"t": "x"})
        .child("p2", "j2", node_type="item", content={"t": "x"})
        .build()
    )
    result = reconcile(src, tgt)

    assert not result.operations.of_type(OperationType.MOVE)
    assert not result.operations.of_type(OperationType.DELETE)
    assert not result.operations.of_type(OperationType.INSERT)
    # Both sides of the divergence are held as unresolved, on either parent.
    assert set(result.alignment.unresolved_region_ids) == {
        "region:p1->p1",
        "region:p2->p2",
    }
    assert result.alignment.unresolved_source_refs == frozenset({"i1", "i2"})
    assert result.alignment.unresolved_target_refs == frozenset({"j1", "j2"})

    localized = localize(src, tgt)
    present = set(statuses(localized))
    assert "AMBIGUOUS_MATCH" in present
    assert present.isdisjoint({"MISSING_IN_LOCALE", "EXTRA_IN_LOCALE", "WRONG_PARENT"})


# -- D. The localization layer never emits contradictory statuses ----------


def test_localization_never_pairs_ambiguity_with_a_presence_status() -> None:
    """No node may carry both an ambiguity and a presence finding.

    Covers every fixture in this module rather than one hand-picked case, since
    the contradiction is a property of the interpretation, not of one shape.
    """
    for src, tgt in (_repeated_siblings(), _mixed_region()):
        result = localize(src, tgt)
        ambiguous_sources = {
            c.source_node_ref for c in result.reconciliation.match_graph.ambiguous
        }
        ambiguous_targets = {
            c.target_node_ref for c in result.reconciliation.match_graph.ambiguous
        }
        for issue in result.issues:
            if issue.localization_status.value == "MISSING_IN_LOCALE":
                assert issue.source_node_ref not in ambiguous_sources
            if issue.localization_status.value == "EXTRA_IN_LOCALE":
                assert issue.locale_node_ref not in ambiguous_targets
