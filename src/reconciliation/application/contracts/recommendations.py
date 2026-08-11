"""Repair recommendation contract (SRS §8.5, REQ-117-127, REQ-272-275).

Recommendations are *proposals*, never applied (REQ-117, REQ-125, AC-037).
Every recommendation is non-executable in the initial release, lists explicit
machine-readable preconditions and postconditions (REQ-272, REQ-273, AC-039),
declares which aspects it would change (REQ-275), carries a *repair* confidence
distinct from match/operation confidence (REQ-120, REQ-276), and identifies the
authoritative side and target (REQ-121, AC-040).
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field, model_validator

from reconciliation.application.contracts.common import AuthoritativeSide
from reconciliation.core.contracts.base import StrictModel
from reconciliation.core.contracts.tree import NodeRef


class RepairOperation(str, Enum):
    """The kind of correction a recommendation proposes."""

    MOVE_NODE = "MOVE_NODE"
    REORDER_NODES = "REORDER_NODES"
    ADD_NODE = "ADD_NODE"
    REMOVE_NODE = "REMOVE_NODE"
    REVIEW_TRANSLATION = "REVIEW_TRANSLATION"


class RepairChange(str, Enum):
    """Which aspect of the tree a recommendation would change (REQ-275)."""

    CONTAINMENT = "CONTAINMENT"
    ORDER = "ORDER"
    IDENTITY = "IDENTITY"
    CONTENT = "CONTENT"


class RepairRecommendation(StrictModel):
    """A single, non-executable repair recommendation.

    :ivar recommendation_id: Stable identifier.
    :ivar operation: The proposed correction kind.
    :ivar authoritative_side: The tree treated as the desired target (REQ-121).
    :ivar target_side: The tree the correction would apply to.
    :ivar issue_id: The localization issue this addresses.
    :ivar source_operation_ids: Core operations that motivated it (REQ-119).
    :ivar target_node_ref: The node to be corrected, when applicable.
    :ivar destination_parent_ref: Destination parent for a move/add.
    :ivar after_sibling_ref: Sibling the node should follow, when known.
    :ivar before_sibling_ref: Sibling the node should precede, when known.
    :ivar repair_confidence: Confidence in correction safety (REQ-120).
    :ivar executable: Always False in the initial release (REQ-125).
    :ivar auto_fix_eligible: Always False in the initial release (REQ-124).
    :ivar changes: Aspects the correction would change (REQ-275).
    :ivar preconditions: Machine-readable preconditions (REQ-272, AC-039).
    :ivar postconditions: Expected corrected state (REQ-273).
    """

    recommendation_id: str = Field(min_length=1)
    operation: RepairOperation
    authoritative_side: AuthoritativeSide
    target_side: AuthoritativeSide
    issue_id: str = Field(min_length=1)
    source_operation_ids: tuple[str, ...] = ()
    target_node_ref: NodeRef | None = None
    destination_parent_ref: NodeRef | None = None
    after_sibling_ref: NodeRef | None = None
    before_sibling_ref: NodeRef | None = None
    repair_confidence: float = Field(ge=0.0, le=1.0)
    executable: bool = False
    auto_fix_eligible: bool = False
    changes: frozenset[RepairChange]
    preconditions: tuple[str, ...]
    postconditions: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _safety_invariants(self) -> RepairRecommendation:
        if self.executable:
            raise ValueError(
                "recommendations must not be executable in the initial release (REQ-125)"
            )
        if self.auto_fix_eligible:
            raise ValueError("auto_fix_eligible must be False in the initial release (REQ-124)")
        if not self.preconditions:
            raise ValueError("a recommendation must list explicit preconditions (AC-039)")
        if not self.changes:
            raise ValueError("a recommendation must declare what it changes (REQ-275)")
        return self
