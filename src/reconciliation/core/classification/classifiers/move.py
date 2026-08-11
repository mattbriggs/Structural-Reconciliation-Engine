"""MOVE classifier (REQ-066, REQ-070, AC-004, AC-005).

A ``MOVE`` requires a confirmed correspondence whose source and target sit
under non-corresponding parents *and* whose confidence clears the operation
profile's move threshold. Below-threshold candidates are deliberately not
emitted here; they degrade to DELETE + INSERT (REQ-071).
"""

from __future__ import annotations

from reconciliation.core.classification.registry import ClassificationContext
from reconciliation.core.contracts.evidence import Confidence
from reconciliation.core.contracts.operations import StructuralOperation
from reconciliation.core.contracts.profiles import OperationType
from reconciliation.core.matching.matcher import _match_id


class MoveClassifier:
    """Classifies above-threshold cross-parent matches as MOVE."""

    name = "move"

    def classify(self, ctx: ClassificationContext) -> tuple[StructuralOperation, ...]:
        """Emit one MOVE per above-threshold cross-parent correspondence."""
        if OperationType.MOVE not in ctx.profile.enabled_operations:
            return ()
        operations: list[StructuralOperation] = []
        for sc, tc in ctx.move_pairs():
            from_parent = ctx.target.nodes[tc].parent_ref
            source_parent = ctx.source.nodes[sc].parent_ref
            # Represent the move in the target tree's terms: the node's parent
            # differs from the parent that corresponds to its source parent.
            to_parent = from_parent
            expected_parent = (
                ctx.graph.confirmed_target_for(source_parent)
                if source_parent is not None
                else None
            )
            operations.append(
                StructuralOperation(
                    operation_id=f"op:move:{sc}->{tc}",
                    type=OperationType.MOVE,
                    source_node_refs=(sc,),
                    target_node_refs=(tc,),
                    from_parent_ref=expected_parent,
                    to_parent_ref=to_parent,
                    confidence=Confidence(value=ctx.confirmed_confidence(sc, tc)),
                    match_ids=(_match_id(sc, tc),),
                    evidence_codes=("CONFIRMED_IDENTITY", "PARENT_CHANGED"),
                    preconditions=("SOURCE_AND_TARGET_MATCH_REMAINS_VALID",),
                )
            )
        return tuple(operations)
