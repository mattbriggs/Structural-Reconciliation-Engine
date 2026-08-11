"""INSERT / DELETE classifier (REQ-068, REQ-069, AC-002, AC-003).

A target-only node with no confirmed correspondence is an ``INSERT``; a
source-only node with no confirmed correspondence is a ``DELETE``. Nodes that
participate in an above-threshold MOVE are excluded (the move classifier owns
them); cross-parent matches *below* the move threshold fall through to here as
DELETE + INSERT (REQ-071).
"""

from __future__ import annotations

from reconciliation.core.classification.registry import ClassificationContext
from reconciliation.core.contracts.alignment import AlignmentEdgeKind
from reconciliation.core.contracts.evidence import Confidence
from reconciliation.core.contracts.operations import StructuralOperation
from reconciliation.core.contracts.profiles import OperationType


class InsertDeleteClassifier:
    """Classifies unmatched source/target nodes as DELETE/INSERT."""

    name = "insert_delete"

    def classify(self, ctx: ClassificationContext) -> tuple[StructuralOperation, ...]:
        """Emit DELETE for source-only and INSERT for target-only nodes."""
        moved_sources = ctx.moved_source_refs()
        moved_targets = ctx.moved_target_refs()
        operations: list[StructuralOperation] = []

        for region in ctx.alignment.regions:
            for pair in region.pairs:
                if pair.kind is AlignmentEdgeKind.SOURCE_ONLY:
                    sc = pair.source_node_ref
                    assert sc is not None
                    if sc in moved_sources:
                        continue
                    if OperationType.DELETE not in ctx.profile.enabled_operations:
                        continue
                    operations.append(
                        StructuralOperation(
                            operation_id=f"op:delete:{sc}",
                            type=OperationType.DELETE,
                            source_node_refs=(sc,),
                            confidence=Confidence(value=1.0),
                            evidence_codes=("SOURCE_ONLY",),
                        )
                    )
                elif pair.kind is AlignmentEdgeKind.TARGET_ONLY:
                    tc = pair.target_node_ref
                    assert tc is not None
                    if tc in moved_targets:
                        continue
                    if OperationType.INSERT not in ctx.profile.enabled_operations:
                        continue
                    operations.append(
                        StructuralOperation(
                            operation_id=f"op:insert:{tc}",
                            type=OperationType.INSERT,
                            target_node_refs=(tc,),
                            confidence=Confidence(value=1.0),
                            evidence_codes=("TARGET_ONLY",),
                        )
                    )
        return tuple(operations)
