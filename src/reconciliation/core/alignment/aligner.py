"""Tree aligner (REQ-052-060).

Given a match graph and both trees, the aligner walks corresponding parent
pairs top-down and aligns their children. Matched children under the *same*
corresponding parent are aligned in sequence; a child matched to a node under a
*different* parent is left-only here (its move is diagnosed by the classifier).

Order semantics are per node type (REQ-054): under an ordered parent, matched
siblings that fall out of the longest common subsequence indicate a reorder
(``order_changed=True``); under an unordered parent, order is ignored
(REQ-097, AC-007).

A child with no confirmed correspondence is *not* automatically one-sided. If
it participates in ambiguous candidate edges, a viable correspondence exists
that simply is not uniquely resolvable, so the position is recorded as
unresolved and its parent region is marked unresolved (REQ-058). Unresolved is
a first-class third state, distinct from confirmed absence: the classifier must
not turn it into a hard presence operation.
"""

from __future__ import annotations

from reconciliation.core.contracts.alignment import (
    AlignedPair,
    AlignedRegion,
    AlignmentEdgeKind,
    AlignmentResult,
)
from reconciliation.core.contracts.matches import MatchGraph
from reconciliation.core.contracts.profiles import AlignmentProfile, OrderSemantics
from reconciliation.core.contracts.tree import CanonicalTree, NodeRef
from reconciliation.core.matching.matcher import _match_id


def region_id_for(source_parent: NodeRef, target_parent: NodeRef) -> str:
    """Return the stable region id for a corresponding parent pair."""
    return f"region:{source_parent}->{target_parent}"


class TreeAlignerService:
    """Default :class:`TreeAligner` implementation."""

    def align(
        self,
        source: CanonicalTree,
        target: CanonicalTree,
        graph: MatchGraph,
        profile: AlignmentProfile,
    ) -> AlignmentResult:
        """Align two trees under an existing match graph.

        :param source: Normalized source tree.
        :param target: Normalized target tree.
        :param graph: Confirmed/ambiguous correspondences.
        :param profile: Alignment configuration.
        :returns: An :class:`AlignmentResult` with one region per corresponding
            parent pair: the roots plus every confirmed correspondence. Aligning
            the children of *every* confirmed pair (not only same-parent ones)
            ensures a moved subtree is still compared internally, so an
            independent defect within it is not missed (AC-014). Regions
            contaminated by ambiguity are reported as unresolved (REQ-058).
        """
        confirmed_sources = {c.source_node_ref for c in graph.confirmed}
        confirmed_targets = {c.target_node_ref for c in graph.confirmed}
        ambiguous_sources = self._ambiguous_index(
            graph, on_source=True, settled=confirmed_sources
        )
        ambiguous_targets = self._ambiguous_index(
            graph, on_source=False, settled=confirmed_targets
        )

        regions: list[AlignedRegion] = []
        # Deduplicated set of corresponding parent pairs to align: the roots and
        # every confirmed match (a matched node is the parent of its subtree).
        parent_pairs: list[tuple[NodeRef, NodeRef]] = [
            (source.root_node_ref, target.root_node_ref)
        ]
        for c in graph.confirmed:
            pair = (c.source_node_ref, c.target_node_ref)
            if pair not in parent_pairs:
                parent_pairs.append(pair)
        for source_parent, target_parent in sorted(parent_pairs):
            self._align_parent(
                source,
                target,
                graph,
                profile,
                source_parent,
                target_parent,
                regions,
                ambiguous_sources,
                ambiguous_targets,
            )
        return AlignmentResult(
            regions=tuple(regions),
            unresolved_region_ids=tuple(r.region_id for r in regions if r.unresolved),
        )

    @staticmethod
    def _ambiguous_index(
        graph: MatchGraph, *, on_source: bool, settled: set[NodeRef]
    ) -> dict[NodeRef, tuple[str, ...]]:
        """Map each node participating in ambiguous edges to those match ids.

        :param settled: Nodes holding a confirmed correspondence on this side.
            They are never listed: a confirmed match settles identity, so such a
            node is not a source of unresolved alignment.
        """
        index: dict[NodeRef, list[str]] = {}
        for candidate in graph.ambiguous:
            ref = candidate.source_node_ref if on_source else candidate.target_node_ref
            if ref in settled:
                continue
            index.setdefault(ref, []).append(candidate.match_id)
        return {ref: tuple(sorted(ids)) for ref, ids in index.items()}

    def _align_parent(
        self,
        source: CanonicalTree,
        target: CanonicalTree,
        graph: MatchGraph,
        profile: AlignmentProfile,
        source_parent: NodeRef,
        target_parent: NodeRef,
        regions: list[AlignedRegion],
        ambiguous_sources: dict[NodeRef, tuple[str, ...]],
        ambiguous_targets: dict[NodeRef, tuple[str, ...]],
    ) -> None:
        source_children = list(source.nodes[source_parent].child_refs)
        target_children = list(target.nodes[target_parent].child_refs)
        target_child_set = set(target_children)

        ordered = (
            profile.order_semantics_for(source.nodes[source_parent].node_type)
            is OrderSemantics.ORDERED
        )

        # Matched sibling pairs: confirmed correspondences whose *both* endpoints
        # are children of this corresponding parent pair. These are always
        # ALIGNED; a change in their relative order is a reorder, not an
        # insert/delete (REQ-067).
        matched_pairs = [
            (sc, tc)
            for sc in source_children
            if (tc := graph.confirmed_target_for(sc)) is not None and tc in target_child_set
        ]
        matched_targets = {tc for _sc, tc in matched_pairs}

        pairs: list[AlignedPair] = []
        for sc, tc in matched_pairs:
            pairs.append(
                AlignedPair(
                    kind=AlignmentEdgeKind.ALIGNED,
                    source_node_ref=sc,
                    target_node_ref=tc,
                    match_id=_match_id(sc, tc),
                )
            )
        for sc in source_children:
            tc = graph.confirmed_target_for(sc)
            if tc is not None and tc in matched_targets:
                continue
            ambiguous_ids = ambiguous_sources.get(sc, ())
            if ambiguous_ids:
                # Candidates exist but none dominates: uncertainty, not absence.
                pairs.append(
                    AlignedPair(
                        kind=AlignmentEdgeKind.UNRESOLVED_SOURCE,
                        source_node_ref=sc,
                        ambiguous_match_ids=ambiguous_ids,
                    )
                )
            else:
                pairs.append(
                    AlignedPair(kind=AlignmentEdgeKind.SOURCE_ONLY, source_node_ref=sc)
                )
        for tc in target_children:
            if tc in matched_targets:
                continue
            ambiguous_ids = ambiguous_targets.get(tc, ())
            if ambiguous_ids:
                pairs.append(
                    AlignedPair(
                        kind=AlignmentEdgeKind.UNRESOLVED_TARGET,
                        target_node_ref=tc,
                        ambiguous_match_ids=ambiguous_ids,
                    )
                )
            else:
                pairs.append(
                    AlignedPair(kind=AlignmentEdgeKind.TARGET_ONLY, target_node_ref=tc)
                )

        # Order change: compare the relative order of matched targets as seen
        # from the source child order versus the target child order. Only
        # meaningful for ordered parents (REQ-097, AC-007).
        order_changed = False
        if ordered and len(matched_pairs) >= 2:
            targets_by_source_order = [tc for _sc, tc in matched_pairs]
            targets_by_target_order = [tc for tc in target_children if tc in matched_targets]
            order_changed = targets_by_source_order != targets_by_target_order

        regions.append(
            AlignedRegion(
                region_id=region_id_for(source_parent, target_parent),
                source_parent_ref=source_parent,
                target_parent_ref=target_parent,
                ordered=ordered,
                pairs=tuple(pairs),
                order_changed=order_changed,
                unresolved=any(pair.is_unresolved for pair in pairs),
            )
        )
