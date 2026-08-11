"""Tree aligner (REQ-052-060).

Given a match graph and both trees, the aligner walks corresponding parent
pairs top-down and aligns their children. Matched children under the *same*
corresponding parent are aligned in sequence; a child matched to a node under a
*different* parent is left-only here (its move is diagnosed by the classifier).

Order semantics are per node type (REQ-054): under an ordered parent, matched
siblings that fall out of the longest common subsequence indicate a reorder
(``order_changed=True``); under an unordered parent, order is ignored
(REQ-097, AC-007).
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
            independent defect within it is not missed (AC-014).
        """
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
                source, target, graph, profile, source_parent, target_parent, regions
            )
        return AlignmentResult(regions=tuple(regions))

    def _align_parent(
        self,
        source: CanonicalTree,
        target: CanonicalTree,
        graph: MatchGraph,
        profile: AlignmentProfile,
        source_parent: NodeRef,
        target_parent: NodeRef,
        regions: list[AlignedRegion],
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
            if tc is None or tc not in matched_targets:
                pairs.append(
                    AlignedPair(kind=AlignmentEdgeKind.SOURCE_ONLY, source_node_ref=sc)
                )
        for tc in target_children:
            if tc not in matched_targets:
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
                source_parent_ref=source_parent,
                target_parent_ref=target_parent,
                ordered=ordered,
                pairs=tuple(pairs),
                order_changed=order_changed,
            )
        )
