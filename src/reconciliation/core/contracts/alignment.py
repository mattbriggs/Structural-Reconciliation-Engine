"""Structural alignment contracts (REQ-052-060).

Alignment organizes confirmed/candidate correspondences into a structurally
coherent relationship. The result is expressed in domain-neutral terms and
must not reference localization issue terminology (REQ-059).
"""

from __future__ import annotations

from enum import Enum

from reconciliation.core.contracts.base import StrictModel
from reconciliation.core.contracts.tree import NodeRef


class AlignmentEdgeKind(str, Enum):
    """Kind of positional relationship between aligned nodes."""

    ALIGNED = "ALIGNED"
    SOURCE_ONLY = "SOURCE_ONLY"
    TARGET_ONLY = "TARGET_ONLY"


class AlignedPair(StrictModel):
    """One aligned position within a parent's child sequence.

    :ivar kind: Whether the position is matched or present on one side only.
    :ivar source_node_ref: Source child reference, if present.
    :ivar target_node_ref: Target child reference, if present.
    :ivar match_id: Confirmed match backing an ALIGNED pair, if any.
    """

    kind: AlignmentEdgeKind
    source_node_ref: NodeRef | None = None
    target_node_ref: NodeRef | None = None
    match_id: str | None = None


class AlignedRegion(StrictModel):
    """Alignment of the children of a corresponding parent pair.

    :ivar source_parent_ref: Source parent node reference (None at forest top).
    :ivar target_parent_ref: Target parent node reference (None at forest top).
    :ivar ordered: Whether order was treated as significant (REQ-054).
    :ivar pairs: Ordered aligned positions.
    :ivar order_changed: True when matched siblings changed relative order
        (REQ-067) under an ordered parent.
    """

    source_parent_ref: NodeRef | None = None
    target_parent_ref: NodeRef | None = None
    ordered: bool = True
    pairs: tuple[AlignedPair, ...] = ()
    order_changed: bool = False


class AlignmentResult(StrictModel):
    """Complete structural alignment between two trees (REQ-060).

    :ivar regions: Per-parent aligned regions in deterministic order.
    :ivar unresolved_region_ids: Identifiers of regions retained as unresolved
        because no candidate alignment dominated (REQ-058).
    """

    regions: tuple[AlignedRegion, ...] = ()
    unresolved_region_ids: tuple[str, ...] = ()

    def region_for(
        self, source_parent_ref: NodeRef | None, target_parent_ref: NodeRef | None
    ) -> AlignedRegion | None:
        """Return the region for a given source/target parent pair, if present."""
        for region in self.regions:
            if (
                region.source_parent_ref == source_parent_ref
                and region.target_parent_ref == target_parent_ref
            ):
                return region
        return None
