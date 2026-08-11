"""Structural operation contracts (REQ-061-072, REQ-259-263).

Operations are domain-neutral: ``MATCH``, ``INSERT``, ``DELETE``, ``UPDATE``,
``MOVE``, ``REORDER`` in the initial release. Operation-specific invariants
(a REORDER references >= 2 matched siblings; a MOVE identifies a changed
parent/region) are enforced at model level so no downstream stage can rely on
malformed operations.
"""

from __future__ import annotations

from pydantic import Field, model_validator

from reconciliation.core.contracts.base import StrictModel
from reconciliation.core.contracts.evidence import Confidence
from reconciliation.core.contracts.profiles import OperationType
from reconciliation.core.contracts.tree import NodeRef


class StructuralOperation(StrictModel):
    """A single classified structural operation.

    :ivar operation_id: Stable identifier.
    :ivar type: Operation type (REQ-061).
    :ivar source_node_refs: Affected source nodes.
    :ivar target_node_refs: Affected target nodes.
    :ivar from_parent_ref: Prior parent for a MOVE (REQ-263).
    :ivar to_parent_ref: New parent for a MOVE (REQ-263).
    :ivar confidence: Operation confidence (REQ-063, REQ-261).
    :ivar match_ids: Supporting confirmed matches (REQ-259).
    :ivar evidence_codes: Machine-readable evidence codes (REQ-063).
    :ivar preconditions: Operation preconditions (REQ-063).
    """

    operation_id: str = Field(min_length=1)
    type: OperationType
    source_node_refs: tuple[NodeRef, ...] = ()
    target_node_refs: tuple[NodeRef, ...] = ()
    from_parent_ref: NodeRef | None = None
    to_parent_ref: NodeRef | None = None
    confidence: Confidence
    match_ids: tuple[str, ...] = ()
    evidence_codes: tuple[str, ...] = ()
    preconditions: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _operation_specific_invariants(self) -> StructuralOperation:
        if self.type is OperationType.REORDER:
            matched_siblings = len(self.source_node_refs)
            if matched_siblings < 2:
                raise ValueError("REORDER must reference at least two matched siblings (REQ-262)")
        if self.type is OperationType.MOVE:
            if self.from_parent_ref == self.to_parent_ref:
                raise ValueError("MOVE must identify a changed parent or region (REQ-263)")
            if not self.match_ids:
                raise ValueError("MOVE must reference supporting correspondence (REQ-259, REQ-066)")
        # Operations other than unmatched insert/delete require correspondence.
        if self.type in (OperationType.MATCH, OperationType.UPDATE) and not self.match_ids:
            raise ValueError(
                f"{self.type.value} must reference supporting correspondence (REQ-259)"
            )
        return self


class StructuralOperationSet(StrictModel):
    """The full set of classified operations (contract to the analyzer).

    :ivar operations: Operations in deterministic order.
    """

    operations: tuple[StructuralOperation, ...] = ()

    def of_type(self, operation_type: OperationType) -> tuple[StructuralOperation, ...]:
        """Return operations of a given type."""
        return tuple(op for op in self.operations if op.type is operation_type)
