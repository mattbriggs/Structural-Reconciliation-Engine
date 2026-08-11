"""MATCH / UPDATE classifier (REQ-061, REQ-065, AC-001, AC-008).

Aligned pairs sit under corresponding parents by construction of the aligner.
An aligned pair whose content properties are unchanged is a ``MATCH``; a change
in content with preserved identity is an ``UPDATE`` (never delete + insert,
AC-008).
"""

from __future__ import annotations

from reconciliation.core.classification.registry import ClassificationContext
from reconciliation.core.contracts.alignment import AlignmentEdgeKind
from reconciliation.core.contracts.evidence import Confidence
from reconciliation.core.contracts.operations import StructuralOperation
from reconciliation.core.contracts.profiles import OperationType
from reconciliation.core.matching.matcher import _match_id


class MatchUpdateClassifier:
    """Classifies aligned pairs as MATCH or UPDATE."""

    name = "match_update"

    def classify(self, ctx: ClassificationContext) -> tuple[StructuralOperation, ...]:
        """Emit a MATCH or UPDATE for each aligned pair."""
        operations: list[StructuralOperation] = []
        for region in ctx.alignment.regions:
            for pair in region.pairs:
                if pair.kind is not AlignmentEdgeKind.ALIGNED:
                    continue
                sc = pair.source_node_ref
                tc = pair.target_node_ref
                assert sc is not None and tc is not None
                confidence = ctx.confirmed_confidence(sc, tc)
                changed = (
                    ctx.source.nodes[sc].content_properties
                    != ctx.target.nodes[tc].content_properties
                )
                op_type = OperationType.UPDATE if changed else OperationType.MATCH
                if op_type not in ctx.profile.enabled_operations:
                    continue
                operations.append(
                    StructuralOperation(
                        operation_id=f"op:{op_type.value.lower()}:{sc}->{tc}",
                        type=op_type,
                        source_node_refs=(sc,),
                        target_node_refs=(tc,),
                        confidence=Confidence(value=confidence),
                        match_ids=(_match_id(sc, tc),),
                        evidence_codes=(
                            ("CONTENT_CHANGED",) if changed else ("IDENTITY_PRESERVED",)
                        ),
                    )
                )
        return tuple(operations)
