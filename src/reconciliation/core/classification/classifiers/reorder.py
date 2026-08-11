"""REORDER classifier (REQ-067, REQ-262, AC-006, AC-007).

A ``REORDER`` is emitted for an ordered parent region whose matched siblings
changed relative order. It requires at least two matched siblings; under an
unordered parent no reorder is ever reported (AC-007).
"""

from __future__ import annotations

from reconciliation.core.classification.registry import ClassificationContext
from reconciliation.core.contracts.alignment import AlignmentEdgeKind
from reconciliation.core.contracts.evidence import Confidence
from reconciliation.core.contracts.operations import StructuralOperation
from reconciliation.core.contracts.profiles import OperationType
from reconciliation.core.matching.matcher import _match_id


class ReorderClassifier:
    """Classifies order changes among matched siblings as REORDER."""

    name = "reorder"

    def classify(self, ctx: ClassificationContext) -> tuple[StructuralOperation, ...]:
        """Emit one REORDER per ordered region whose siblings changed order."""
        if OperationType.REORDER not in ctx.profile.enabled_operations:
            return ()
        operations: list[StructuralOperation] = []
        for region in ctx.alignment.regions:
            if not (region.ordered and region.order_changed):
                continue
            matched = [
                p for p in region.pairs if p.kind is AlignmentEdgeKind.ALIGNED
            ]
            if len(matched) < 2:
                continue
            source_refs = tuple(p.source_node_ref for p in matched if p.source_node_ref)
            target_refs = tuple(p.target_node_ref for p in matched if p.target_node_ref)
            match_ids = tuple(
                _match_id(p.source_node_ref, p.target_node_ref)
                for p in matched
                if p.source_node_ref and p.target_node_ref
            )
            operations.append(
                StructuralOperation(
                    operation_id=f"op:reorder:{region.source_parent_ref}",
                    type=OperationType.REORDER,
                    source_node_refs=source_refs,
                    target_node_refs=target_refs,
                    confidence=Confidence(value=1.0),
                    match_ids=match_ids,
                    evidence_codes=("SIBLING_ORDER_CHANGED",),
                )
            )
        return tuple(operations)
