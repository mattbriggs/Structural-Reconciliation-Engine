"""Structural alignment contracts (REQ-052-060).

Alignment organizes confirmed/candidate correspondences into a structurally
coherent relationship. The result is expressed in domain-neutral terms and
must not reference localization issue terminology (REQ-059).

The contracts keep three states apart, which is the whole point of the model:

1. **Confirmed correspondence** — an ``ALIGNED`` pair.
2. **Confirmed absence** — a ``SOURCE_ONLY`` / ``TARGET_ONLY`` position: no
   viable correspondence exists for that node.
3. **Unresolved ambiguity** — an ``UNRESOLVED_SOURCE`` / ``UNRESOLVED_TARGET``
   position: a viable correspondence exists but is not uniquely resolvable
   (REQ-058). Absence is *not* claimed, so downstream stages must not convert
   these positions into presence defects.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field, model_validator

from reconciliation.core.contracts.base import StrictModel
from reconciliation.core.contracts.tree import NodeRef


class AlignmentEdgeKind(str, Enum):
    """Kind of positional relationship between aligned nodes.

    ``SOURCE_ONLY`` / ``TARGET_ONLY`` assert absence: no viable correspondence
    was found. ``UNRESOLVED_SOURCE`` / ``UNRESOLVED_TARGET`` assert only
    uncertainty: candidate correspondences exist but none dominates (REQ-058).
    """

    ALIGNED = "ALIGNED"
    SOURCE_ONLY = "SOURCE_ONLY"
    TARGET_ONLY = "TARGET_ONLY"
    UNRESOLVED_SOURCE = "UNRESOLVED_SOURCE"
    UNRESOLVED_TARGET = "UNRESOLVED_TARGET"


#: Positions whose correspondence is unresolved rather than absent (REQ-058).
UNRESOLVED_EDGE_KINDS: frozenset[AlignmentEdgeKind] = frozenset(
    {AlignmentEdgeKind.UNRESOLVED_SOURCE, AlignmentEdgeKind.UNRESOLVED_TARGET}
)


class AlignedPair(StrictModel):
    """One aligned position within a parent's child sequence.

    :ivar kind: Whether the position is matched, present on one side only, or
        unresolved.
    :ivar source_node_ref: Source child reference, if present.
    :ivar target_node_ref: Target child reference, if present.
    :ivar match_id: Confirmed match backing an ALIGNED pair, if any.
    :ivar ambiguous_match_ids: Candidate matches that make an unresolved
        position unresolved rather than absent (REQ-058, REQ-256).
    """

    kind: AlignmentEdgeKind
    source_node_ref: NodeRef | None = None
    target_node_ref: NodeRef | None = None
    match_id: str | None = None
    ambiguous_match_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _validate_kind_consistency(self) -> AlignedPair:
        """An unresolved position must name the candidates that make it so."""
        if self.kind is AlignmentEdgeKind.ALIGNED and (
            self.source_node_ref is None or self.target_node_ref is None
        ):
            raise ValueError("an ALIGNED pair requires both a source and a target node")
        if self.is_unresolved and not self.ambiguous_match_ids:
            raise ValueError(
                f"{self.kind.value} position must reference at least one ambiguous "
                "candidate match (REQ-058)"
            )
        return self

    @property
    def is_unresolved(self) -> bool:
        """True when the position records ambiguity rather than absence."""
        return self.kind in UNRESOLVED_EDGE_KINDS


class AlignedRegion(StrictModel):
    """Alignment of the children of a corresponding parent pair.

    :ivar region_id: Stable, deterministic identifier for this region (REQ-060).
    :ivar source_parent_ref: Source parent node reference (None at forest top).
    :ivar target_parent_ref: Target parent node reference (None at forest top).
    :ivar ordered: Whether order was treated as significant (REQ-054).
    :ivar pairs: Ordered aligned positions.
    :ivar order_changed: True when matched siblings changed relative order
        (REQ-067) under an ordered parent.
    :ivar unresolved: True when the region contains at least one unresolved
        position, so its structural interpretation is not settled (REQ-058).
    """

    region_id: str = Field(min_length=1)
    source_parent_ref: NodeRef | None = None
    target_parent_ref: NodeRef | None = None
    ordered: bool = True
    pairs: tuple[AlignedPair, ...] = ()
    order_changed: bool = False
    unresolved: bool = False

    @model_validator(mode="after")
    def _unresolved_positions_mark_the_region(self) -> AlignedRegion:
        if any(pair.is_unresolved for pair in self.pairs) and not self.unresolved:
            raise ValueError(
                f"region {self.region_id!r} holds unresolved positions and must be "
                "marked unresolved (REQ-058)"
            )
        return self

    @property
    def unresolved_source_refs(self) -> tuple[NodeRef, ...]:
        """Source children whose correspondence is unresolved, in region order."""
        return tuple(
            pair.source_node_ref
            for pair in self.pairs
            if pair.kind is AlignmentEdgeKind.UNRESOLVED_SOURCE
            and pair.source_node_ref is not None
        )

    @property
    def unresolved_target_refs(self) -> tuple[NodeRef, ...]:
        """Target children whose correspondence is unresolved, in region order."""
        return tuple(
            pair.target_node_ref
            for pair in self.pairs
            if pair.kind is AlignmentEdgeKind.UNRESOLVED_TARGET
            and pair.target_node_ref is not None
        )


class AlignmentResult(StrictModel):
    """Complete structural alignment between two trees (REQ-060).

    :ivar regions: Per-parent aligned regions in deterministic order.
    :ivar unresolved_region_ids: Identifiers of regions retained as unresolved
        because no candidate alignment dominated (REQ-058).

    Invariant: ``unresolved_region_ids`` is exactly the set of region ids whose
    region is marked unresolved, so a reader can trust either representation.
    """

    regions: tuple[AlignedRegion, ...] = ()
    unresolved_region_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _unresolved_ids_match_regions(self) -> AlignmentResult:
        ids = [region.region_id for region in self.regions]
        if len(set(ids)) != len(ids):
            raise ValueError("aligned region ids must be unique")
        listed = set(self.unresolved_region_ids)
        if len(listed) != len(self.unresolved_region_ids):
            raise ValueError("unresolved_region_ids must not contain duplicates")
        marked = {region.region_id for region in self.regions if region.unresolved}
        if listed != marked:
            raise ValueError(
                "unresolved_region_ids must list exactly the unresolved regions; "
                f"missing={sorted(marked - listed)} unknown={sorted(listed - marked)}"
            )
        return self

    @property
    def unresolved_regions(self) -> tuple[AlignedRegion, ...]:
        """Regions whose structural interpretation is unresolved (REQ-058)."""
        return tuple(region for region in self.regions if region.unresolved)

    @property
    def unresolved_source_refs(self) -> frozenset[NodeRef]:
        """Every source node whose correspondence is unresolved."""
        return frozenset(
            ref for region in self.regions for ref in region.unresolved_source_refs
        )

    @property
    def unresolved_target_refs(self) -> frozenset[NodeRef]:
        """Every target node whose correspondence is unresolved."""
        return frozenset(
            ref for region in self.regions for ref in region.unresolved_target_refs
        )

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

    def region_by_id(self, region_id: str) -> AlignedRegion | None:
        """Return the region with ``region_id``, if present."""
        for region in self.regions:
            if region.region_id == region_id:
                return region
        return None
