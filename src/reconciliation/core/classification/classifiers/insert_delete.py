"""INSERT / DELETE classifier (REQ-068, REQ-069, AC-002, AC-003).

A target-only node with no viable correspondence is an ``INSERT``; a source-only
node with no viable correspondence is a ``DELETE``. Nodes that participate in an
above-threshold MOVE are excluded (the move classifier owns them); cross-parent
matches *below* the move threshold fall through to here as DELETE + INSERT
(REQ-071).

Unresolved positions are deliberately *not* classified here. ``DELETE`` and
``INSERT`` assert that no viable correspondence exists; a node with ambiguous
candidates has one that merely cannot be resolved uniquely, and reporting it as
absent is the cascade-noise failure this engine exists to prevent (REQ-058).
The ambiguity stays visible in the match graph and the alignment result, and the
``unresolved_presence_policy`` decides how cautious to be.
"""

from __future__ import annotations

from reconciliation.core.classification.registry import ClassificationContext
from reconciliation.core.contracts.alignment import AlignmentEdgeKind
from reconciliation.core.contracts.evidence import Confidence
from reconciliation.core.contracts.operations import StructuralOperation
from reconciliation.core.contracts.profiles import OperationType


def _evidence_codes(side_code: str, unresolved: bool) -> tuple[str, ...]:
    """Return the evidence codes for a presence operation.

    An operation emitted over an unresolved position (only possible under the
    ``EMIT_ALL`` policy) says so, so the audit trail never presents a
    policy-forced conclusion as clean one-sided evidence.
    """
    if unresolved:
        return (side_code, "UNRESOLVED_CORRESPONDENCE_FORCED_BY_POLICY")
    return (side_code,)


class InsertDeleteClassifier:
    """Classifies confidently unmatched source/target nodes as DELETE/INSERT."""

    name = "insert_delete"

    def classify(self, ctx: ClassificationContext) -> tuple[StructuralOperation, ...]:
        """Emit DELETE for source-only and INSERT for target-only nodes."""
        moved_sources = ctx.moved_source_refs()
        moved_targets = ctx.moved_target_refs()
        operations: list[StructuralOperation] = []

        for region in ctx.alignment.regions:
            if ctx.presence_suppressed_region(region):
                continue
            for pair in region.pairs:
                if pair.kind is AlignmentEdgeKind.ALIGNED:
                    continue
                if ctx.presence_suppressed_pair(pair):
                    continue
                if pair.kind in (
                    AlignmentEdgeKind.SOURCE_ONLY,
                    AlignmentEdgeKind.UNRESOLVED_SOURCE,
                ):
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
                            evidence_codes=_evidence_codes("SOURCE_ONLY", pair.is_unresolved),
                        )
                    )
                else:
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
                            evidence_codes=_evidence_codes("TARGET_ONLY", pair.is_unresolved),
                        )
                    )
        return tuple(operations)
