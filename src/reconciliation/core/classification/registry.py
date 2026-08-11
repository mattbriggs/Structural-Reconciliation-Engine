"""Classifier registry and shared context (Registry pattern, REQ-062).

New operation classifiers register here without any change to the matcher or
aligner (AC-032, REQ-231). Each classifier receives an immutable
:class:`ClassificationContext` and returns structural operations; the
orchestrating classifier concatenates and deterministically orders them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from reconciliation.core.contracts.alignment import AlignmentResult
from reconciliation.core.contracts.matches import MatchGraph, MatchState
from reconciliation.core.contracts.operations import StructuralOperation
from reconciliation.core.contracts.profiles import OperationProfile
from reconciliation.core.contracts.tree import CanonicalTree, NodeRef


@dataclass(frozen=True)
class ClassificationContext:
    """Read-only inputs shared by every classifier.

    :ivar source: Normalized source tree.
    :ivar target: Normalized target tree.
    :ivar graph: Confirmed/ambiguous correspondences.
    :ivar alignment: Structural alignment result.
    :ivar profile: Operation profile (enabled ops, thresholds).
    """

    source: CanonicalTree
    target: CanonicalTree
    graph: MatchGraph
    alignment: AlignmentResult
    profile: OperationProfile

    def parents_correspond(self, source_parent: NodeRef, target_parent: NodeRef) -> bool:
        """True if two parents are the tree roots or a confirmed match."""
        if source_parent == self.source.root_node_ref and (
            target_parent == self.target.root_node_ref
        ):
            return True
        return self.graph.confirmed_target_for(source_parent) == target_parent

    def confirmed_confidence(self, source_ref: NodeRef, target_ref: NodeRef) -> float:
        """Return the confidence of a confirmed match, or 0.0 if none."""
        for c in self.graph.candidates:
            if (
                c.state is MatchState.CONFIRMED
                and c.source_node_ref == source_ref
                and c.target_node_ref == target_ref
            ):
                return c.confidence.value
        return 0.0

    def confirmed_pairs(self) -> tuple[tuple[NodeRef, NodeRef], ...]:
        """Return confirmed (source, target) pairs in deterministic order."""
        return tuple(
            (c.source_node_ref, c.target_node_ref)
            for c in sorted(
                self.graph.confirmed,
                key=lambda c: (c.source_node_ref, c.target_node_ref),
            )
        )

    def is_cross_parent(self, source_ref: NodeRef, target_ref: NodeRef) -> bool:
        """True if a confirmed pair sits under non-corresponding parents (a move)."""
        source_parent = self.source.nodes[source_ref].parent_ref
        target_parent = self.target.nodes[target_ref].parent_ref
        if source_parent is None or target_parent is None:
            return False
        return not self.parents_correspond(source_parent, target_parent)

    def move_pairs(self) -> tuple[tuple[NodeRef, NodeRef], ...]:
        """Cross-parent confirmed pairs whose confidence clears the move threshold.

        Below-threshold cross-parent matches are intentionally excluded so the
        insert/delete classifiers represent them as DELETE + INSERT (REQ-070,
        REQ-071, AC-005).
        """
        threshold = self.profile.move_confidence_threshold
        return tuple(
            (s, t)
            for s, t in self.confirmed_pairs()
            if self.is_cross_parent(s, t) and self.confirmed_confidence(s, t) >= threshold
        )

    def moved_source_refs(self) -> frozenset[NodeRef]:
        """Source refs participating in an above-threshold MOVE."""
        return frozenset(s for s, _t in self.move_pairs())

    def moved_target_refs(self) -> frozenset[NodeRef]:
        """Target refs participating in an above-threshold MOVE."""
        return frozenset(t for _s, t in self.move_pairs())


class OperationClassifier(Protocol):
    """Structural substitutability contract for a classifier (REQ-062)."""

    name: str

    def classify(self, ctx: ClassificationContext) -> tuple[StructuralOperation, ...]:
        """Return the operations this classifier detects for ``ctx``."""
        ...


class ClassifierRegistry:
    """Ordered registry of operation classifiers.

    Registration order is preserved and used as a deterministic secondary sort
    key so results are stable regardless of insertion timing.
    """

    def __init__(self) -> None:
        self._classifiers: list[OperationClassifier] = []

    def register(self, classifier: OperationClassifier) -> None:
        """Register a classifier. Duplicate names are rejected."""
        if any(c.name == classifier.name for c in self._classifiers):
            raise ValueError(f"classifier {classifier.name!r} already registered")
        self._classifiers.append(classifier)

    def classifiers(self) -> tuple[OperationClassifier, ...]:
        """Return registered classifiers in registration order."""
        return tuple(self._classifiers)
