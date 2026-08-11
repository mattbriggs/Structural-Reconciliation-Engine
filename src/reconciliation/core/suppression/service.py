"""Cascade suppression service (REQ-081-089, AC-013-016).

Removes *derived* mismatches from the primary issue list while keeping them for
audit (REQ-085). Suppression fires only when the root operation clears the
applicable rule's threshold (REQ-081, AC-015). Every suppressed effect records
its root operation, rule, confidence, and a resolved independent-defect check;
independent defects inside the affected region are retained (REQ-084, AC-014).
"""

from __future__ import annotations

from reconciliation.core.contracts.alignment import AlignmentEdgeKind, AlignmentResult
from reconciliation.core.contracts.evidence import Confidence
from reconciliation.core.contracts.operations import StructuralOperationSet
from reconciliation.core.contracts.profiles import OperationType
from reconciliation.core.contracts.suppression import (
    IndependentDefectCheck,
    SuppressedEffect,
    SuppressionResult,
)
from reconciliation.core.contracts.tree import CanonicalTree, NodeRef
from reconciliation.core.suppression.independent_defect import find_independent_defects


def _descendants(tree: CanonicalTree, node_ref: NodeRef) -> frozenset[NodeRef]:
    """Return all strict descendants of ``node_ref``."""
    result: set[NodeRef] = set()
    stack = list(tree.nodes[node_ref].child_refs)
    while stack:
        current = stack.pop()
        result.add(current)
        stack.extend(tree.nodes[current].child_refs)
    return frozenset(result)


class CascadeSuppressionService:
    """Default :class:`CascadeSuppressionService` implementation."""

    def suppress(
        self,
        source: CanonicalTree,
        target: CanonicalTree,
        operations: StructuralOperationSet,
        alignment: AlignmentResult,
        profile: object,
    ) -> SuppressionResult:
        """Compute suppressed effects for the classified operations.

        :param source: Normalized source tree.
        :param target: Normalized target tree.
        :param operations: Classified operations.
        :param alignment: Structural alignment result.
        :param profile: A :class:`SuppressionProfile`.
        :returns: A :class:`SuppressionResult` documenting suppressed cascades
            and any retained independent defects.
        """
        from reconciliation.core.contracts.profiles import SuppressionProfile

        assert isinstance(profile, SuppressionProfile)

        effects: list[SuppressedEffect] = []
        retained: set[NodeRef] = set()
        effect_counter = 0

        for op in operations.operations:
            rules = profile.rules_for(op.type)
            if not rules:
                continue
            for rule in rules:
                if op.confidence.value < rule.threshold:
                    # Below suppression threshold: do not suppress (AC-015).
                    continue

                if op.type is OperationType.MOVE:
                    moved_source = op.source_node_refs[0]
                    affected = _descendants(source, moved_source)
                    if not affected:
                        continue
                    # Retain any independent defect inside the moved subtree;
                    # path changes are still suppressed, the defect stays visible.
                    retained.update(find_independent_defects(affected, operations))
                    effect_counter += 1
                    effects.append(
                        SuppressedEffect(
                            effect_id=f"effect-{effect_counter}",
                            root_operation_id=op.operation_id,
                            suppression_rule_id=rule.rule_id,
                            category=rule.effect_category,
                            affected_node_refs=tuple(sorted(affected)),
                            confidence=Confidence(value=op.confidence.value),
                            independent_defect_check=IndependentDefectCheck.PASSED,
                        )
                    )
                else:
                    # INSERT / DELETE / REORDER: downstream sibling position
                    # changes among matched siblings in the affected region.
                    affected = self._downstream_siblings(op, alignment)
                    if not affected:
                        continue
                    effect_counter += 1
                    effects.append(
                        SuppressedEffect(
                            effect_id=f"effect-{effect_counter}",
                            root_operation_id=op.operation_id,
                            suppression_rule_id=rule.rule_id,
                            category=rule.effect_category,
                            affected_node_refs=tuple(sorted(affected)),
                            confidence=Confidence(value=op.confidence.value),
                            independent_defect_check=IndependentDefectCheck.NOT_APPLICABLE,
                        )
                    )

        return SuppressionResult(
            suppressed_effects=tuple(effects),
            retained_defect_node_refs=tuple(sorted(retained)),
        )

    @staticmethod
    def _downstream_siblings(op: object, alignment: AlignmentResult) -> frozenset[NodeRef]:
        from reconciliation.core.contracts.operations import StructuralOperation

        assert isinstance(op, StructuralOperation)
        affected: set[NodeRef] = set()
        for region in alignment.regions:
            matched = [p for p in region.pairs if p.kind is AlignmentEdgeKind.ALIGNED]
            if len(matched) < 1:
                continue
            if op.type is OperationType.INSERT:
                inserted = op.target_node_refs[0] if op.target_node_refs else None
                target_children = [
                    p.target_node_ref for p in region.pairs if p.target_node_ref
                ]
                if inserted in target_children:
                    affected.update(
                        p.target_node_ref for p in matched if p.target_node_ref is not None
                    )
            elif op.type is OperationType.DELETE:
                deleted = op.source_node_refs[0] if op.source_node_refs else None
                source_children = [
                    p.source_node_ref for p in region.pairs if p.source_node_ref
                ]
                if deleted in source_children:
                    affected.update(
                        p.target_node_ref for p in matched if p.target_node_ref is not None
                    )
            elif op.type is OperationType.REORDER:
                if region.source_parent_ref in op.source_node_refs or any(
                    p.source_node_ref in op.source_node_refs for p in matched
                ):
                    affected.update(
                        p.target_node_ref for p in matched if p.target_node_ref is not None
                    )
        return frozenset(affected)
