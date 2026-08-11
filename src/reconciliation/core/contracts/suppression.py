"""Cascade-suppression contracts (REQ-081-089, REQ-264-267).

Suppression removes derived mismatches from the *primary* issue list while
retaining them for audit (REQ-085, REQ-267). A suppressed effect always
references an existing root operation and a resolved independent-defect check.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field, model_validator

from reconciliation.core.contracts.base import StrictModel
from reconciliation.core.contracts.evidence import Confidence
from reconciliation.core.contracts.tree import NodeRef


class IndependentDefectCheck(str, Enum):
    """Outcome of the independent-defect check (REQ-083, REQ-084)."""

    PASSED = "PASSED"
    DEFECT_RETAINED = "DEFECT_RETAINED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class SuppressedEffect(StrictModel):
    """A derived mismatch removed from the primary list but kept for audit.

    :ivar effect_id: Stable identifier.
    :ivar root_operation_id: The root operation that explains this effect
        (REQ-264).
    :ivar suppression_rule_id: Applied suppression rule (REQ-265).
    :ivar category: Effect category (e.g. ``DESCENDANT_PATH_CHANGED``).
    :ivar affected_node_refs: Nodes involved in the derived effect.
    :ivar confidence: Suppression confidence (REQ-086).
    :ivar independent_defect_check: Must be resolved, never unresolved
        (REQ-266).
    :ivar original_severity: Severity the effect would have had if reported.
    """

    effect_id: str = Field(min_length=1)
    root_operation_id: str = Field(min_length=1)
    suppression_rule_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    affected_node_refs: tuple[NodeRef, ...] = ()
    confidence: Confidence
    independent_defect_check: IndependentDefectCheck
    original_severity: str | None = None

    @model_validator(mode="after")
    def _defect_check_resolved(self) -> SuppressedEffect:
        # DEFECT_RETAINED means the effect must NOT have been suppressed; the
        # suppression service only emits PASSED or NOT_APPLICABLE here.
        if self.independent_defect_check is IndependentDefectCheck.DEFECT_RETAINED:
            raise ValueError(
                "a suppressed effect cannot carry a retained independent defect (REQ-084)"
            )
        return self


class SuppressionResult(StrictModel):
    """Output of the suppression service.

    :ivar suppressed_effects: Effects removed from the primary list.
    :ivar retained_defect_node_refs: Nodes where an independent defect was
        detected within a root operation's region and deliberately kept
        visible (REQ-084/AC-014).
    """

    suppressed_effects: tuple[SuppressedEffect, ...] = ()
    retained_defect_node_refs: tuple[NodeRef, ...] = ()

    def counts_by_root(self) -> dict[str, int]:
        """Return suppression counts keyed by root operation (REQ-089)."""
        counts: dict[str, int] = {}
        for effect in self.suppressed_effects:
            counts[effect.root_operation_id] = counts.get(effect.root_operation_id, 0) + 1
        return counts
