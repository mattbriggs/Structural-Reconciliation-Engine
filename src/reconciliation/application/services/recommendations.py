"""Repair recommendation planning (REQ-117-127, AC-037-040).

Generates non-executable recommendations from structural localization issues.
Ambiguous correspondences never yield a recommendation (REQ-123, AC-038);
every recommendation is non-executable (AC-037), lists explicit preconditions
(AC-039), and requires a defined authoritative side (AC-040). Repair confidence
is derived conservatively and is *not* a copy of match confidence (REQ-276).
"""

from __future__ import annotations

from reconciliation.application.contracts.common import AuthoritativeSide
from reconciliation.application.contracts.localization import (
    LocalizationIssue,
    LocalizationStatus,
)
from reconciliation.application.contracts.recommendations import (
    RepairChange,
    RepairOperation,
    RepairRecommendation,
)
from reconciliation.core.contracts.operations import StructuralOperation

#: Repair safety is bounded by, and strictly below, diagnostic confidence: a
#: correct diagnosis does not guarantee a safe automatic correction (REQ-276).
_REPAIR_SAFETY_FACTOR = 0.9

_PRECONDITIONS: dict[RepairOperation, tuple[str, ...]] = {
    RepairOperation.MOVE_NODE: (
        "INPUT_FINGERPRINT_UNCHANGED",
        "TARGET_NODE_EXISTS",
        "DESTINATION_PARENT_EXISTS",
        "DOMAIN_RULES_PASS",
    ),
    RepairOperation.REORDER_NODES: (
        "INPUT_FINGERPRINT_UNCHANGED",
        "MATCHED_SIBLINGS_EXIST",
        "DOMAIN_RULES_PASS",
    ),
    RepairOperation.ADD_NODE: (
        "INPUT_FINGERPRINT_UNCHANGED",
        "DESTINATION_PARENT_EXISTS",
        "SOURCE_NODE_AVAILABLE",
        "DOMAIN_RULES_PASS",
    ),
    RepairOperation.REMOVE_NODE: (
        "INPUT_FINGERPRINT_UNCHANGED",
        "TARGET_NODE_EXISTS",
        "DOMAIN_RULES_PASS",
    ),
}

_POSTCONDITIONS: dict[RepairOperation, tuple[str, ...]] = {
    RepairOperation.MOVE_NODE: (
        "TARGET_PARENT_MATCHES_AUTHORITATIVE_PARENT",
        "XML_REMAINS_SCHEMA_VALID",
    ),
    RepairOperation.REORDER_NODES: (
        "SIBLING_ORDER_MATCHES_AUTHORITATIVE",
        "XML_REMAINS_SCHEMA_VALID",
    ),
    RepairOperation.ADD_NODE: (
        "REQUIRED_NODE_PRESENT_IN_LOCALE",
        "XML_REMAINS_SCHEMA_VALID",
    ),
    RepairOperation.REMOVE_NODE: (
        "EXTRA_NODE_REMOVED_FROM_LOCALE",
        "XML_REMAINS_SCHEMA_VALID",
    ),
}

_CHANGES: dict[RepairOperation, frozenset[RepairChange]] = {
    RepairOperation.MOVE_NODE: frozenset({RepairChange.CONTAINMENT}),
    RepairOperation.REORDER_NODES: frozenset({RepairChange.ORDER}),
    RepairOperation.ADD_NODE: frozenset({RepairChange.CONTAINMENT}),
    RepairOperation.REMOVE_NODE: frozenset({RepairChange.CONTAINMENT}),
}

_STATUS_OPERATION: dict[LocalizationStatus, RepairOperation] = {
    LocalizationStatus.WRONG_PARENT: RepairOperation.MOVE_NODE,
    LocalizationStatus.WRONG_ORDER: RepairOperation.REORDER_NODES,
    LocalizationStatus.MISSING_IN_LOCALE: RepairOperation.ADD_NODE,
    LocalizationStatus.EXTRA_IN_LOCALE: RepairOperation.REMOVE_NODE,
}


class RepairRecommendationService:
    """Plans non-executable repair recommendations from localization issues."""

    def recommend(
        self,
        issues: tuple[LocalizationIssue, ...],
        *,
        authoritative_side: AuthoritativeSide,
        operations_by_id: dict[str, StructuralOperation],
    ) -> tuple[tuple[RepairRecommendation, ...], dict[str, tuple[str, float]]]:
        """Generate recommendations for actionable, unambiguous issues.

        :param issues: Interpreted localization issues.
        :param authoritative_side: The authoritative tree/direction (AC-040).
        :param operations_by_id: Core operations indexed by id, for geometry.
        :returns: ``(recommendations, attachments)`` where ``attachments`` maps
            an issue id to its ``(recommendation_id, repair_confidence)`` so the
            interpreter can link them back (REQ-269).
        """
        target_side = (
            AuthoritativeSide.LOCALE
            if authoritative_side is AuthoritativeSide.SOURCE
            else AuthoritativeSide.SOURCE
        )
        recommendations: list[RepairRecommendation] = []
        attachments: dict[str, tuple[str, float]] = {}
        counter = 0

        for issue in issues:
            operation = _STATUS_OPERATION.get(issue.localization_status)
            if operation is None:
                continue
            if issue.localization_status is LocalizationStatus.AMBIGUOUS_MATCH:
                continue  # never recommend for ambiguity (AC-038)
            if issue.policy_exemption is not None:
                continue  # exempt differences are not defects to repair

            counter += 1
            recommendation_id = f"repair-{counter}"
            repair_confidence = self._repair_confidence(issue)
            destination_parent, after_sibling = self._geometry(issue, operations_by_id)

            recommendations.append(
                RepairRecommendation(
                    recommendation_id=recommendation_id,
                    operation=operation,
                    authoritative_side=authoritative_side,
                    target_side=target_side,
                    issue_id=issue.issue_id,
                    source_operation_ids=issue.core_operation_ids,
                    target_node_ref=issue.locale_node_ref or issue.source_node_ref,
                    destination_parent_ref=destination_parent,
                    after_sibling_ref=after_sibling,
                    repair_confidence=repair_confidence,
                    changes=_CHANGES[operation],
                    preconditions=_PRECONDITIONS[operation],
                    postconditions=_POSTCONDITIONS[operation],
                )
            )
            attachments[issue.issue_id] = (recommendation_id, repair_confidence)

        return tuple(recommendations), attachments

    @staticmethod
    def _repair_confidence(issue: LocalizationIssue) -> float:
        base = min(
            issue.match_confidence if issue.match_confidence is not None else 1.0,
            issue.operation_confidence if issue.operation_confidence is not None else 1.0,
        )
        return round(base * _REPAIR_SAFETY_FACTOR, 6)

    @staticmethod
    def _geometry(
        issue: LocalizationIssue, operations_by_id: dict[str, StructuralOperation]
    ) -> tuple[str | None, str | None]:
        for op_id in issue.core_operation_ids:
            op = operations_by_id.get(op_id)
            if op is not None and op.from_parent_ref is not None:
                # For a MOVE, the authoritative destination is the parent that
                # corresponds to the source parent (recorded as from_parent_ref).
                return op.from_parent_ref, None
        return None, None
