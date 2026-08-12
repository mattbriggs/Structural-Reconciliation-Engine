"""Localization interpretation service (REQ-090-116, REQ-175-177).

Translates a domain-neutral :class:`ReconciliationResult` into source-to-locale
localization issues, applying locale-variation policy (REQ-106) and
translation-state assessment (REQ-110-116). Node-correspondence status is kept
separate from translation currency (REQ-091, REQ-093). Core records are
referenced but never modified (REQ-176). The interpreter then delegates repair
planning and attaches recommendation links back to the issues.
"""

from __future__ import annotations

from reconciliation.application.contracts.common import AuthoritativeSide
from reconciliation.application.contracts.localization import (
    LocalizationIssue,
    LocalizationStatus,
    LocalizationSummary,
    LocalizationValidationResult,
    NodeCounts,
    RecommendedAction,
    TranslationState,
)
from reconciliation.application.contracts.policy import LocaleVariationPolicy
from reconciliation.application.services.locale_policy import LocaleVariationPolicyService
from reconciliation.application.services.recommendations import RepairRecommendationService
from reconciliation.application.services.translation_state import TranslationStateService
from reconciliation.core.contracts.diagnostics import Severity
from reconciliation.core.contracts.operations import StructuralOperation
from reconciliation.core.contracts.profiles import OperationType
from reconciliation.core.contracts.results import ReconciliationResult
from reconciliation.core.contracts.tree import CanonicalNode, CanonicalTree, NodeRef
from reconciliation.version import LOCALIZATION_RESULT_CONTRACT_VERSION

_LABEL_KEYS = ("navtitle", "label", "title")

_SEVERITY: dict[LocalizationStatus, Severity] = {
    LocalizationStatus.CONFIRMED_MATCH: Severity.INFO,
    LocalizationStatus.PROBABLE_MATCH: Severity.INFO,
    LocalizationStatus.EXEMPT_LOCALE_VARIATION: Severity.INFO,
    LocalizationStatus.AMBIGUOUS_MATCH: Severity.WARNING,
    LocalizationStatus.WRONG_ORDER: Severity.WARNING,
    LocalizationStatus.SOURCE_UPDATED: Severity.WARNING,
    LocalizationStatus.EXTRA_IN_LOCALE: Severity.WARNING,
    LocalizationStatus.LOCALE_DIVERGED: Severity.ERROR,
    LocalizationStatus.MISSING_IN_LOCALE: Severity.ERROR,
    LocalizationStatus.WRONG_PARENT: Severity.ERROR,
    LocalizationStatus.IDENTIFIER_CONFLICT: Severity.ERROR,
}

_ACTION: dict[LocalizationStatus, RecommendedAction] = {
    LocalizationStatus.WRONG_PARENT: RecommendedAction.RELINK_OR_MOVE,
    LocalizationStatus.WRONG_ORDER: RecommendedAction.REORDER,
    LocalizationStatus.MISSING_IN_LOCALE: RecommendedAction.ADD_OR_TRANSLATE,
    LocalizationStatus.EXTRA_IN_LOCALE: RecommendedAction.REVIEW_OR_REMOVE,
    LocalizationStatus.AMBIGUOUS_MATCH: RecommendedAction.REVIEW,
    LocalizationStatus.SOURCE_UPDATED: RecommendedAction.REVIEW_TRANSLATION,
}


def _label(node: CanonicalNode | None) -> str | None:
    if node is None:
        return None
    for key in _LABEL_KEYS:
        value = node.content_properties.get(key) or node.identity_properties.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _node_id(node: CanonicalNode | None) -> str | None:
    if node is None:
        return None
    value = node.identity_properties.get("id")
    return str(value) if value is not None else None


class LocalizationValidationService:
    """Interprets a core result into a localization validation result.

    :param translation_service: Translation-state assessor.
    :param policy_service: Locale-variation policy evaluator.
    :param recommendation_service: Repair recommendation planner.
    """

    def __init__(
        self,
        *,
        translation_service: TranslationStateService | None = None,
        policy_service: LocaleVariationPolicyService | None = None,
        recommendation_service: RepairRecommendationService | None = None,
    ) -> None:
        self._translation = translation_service or TranslationStateService()
        self._policy = policy_service or LocaleVariationPolicyService()
        self._recommend = recommendation_service or RepairRecommendationService()

    def validate(
        self,
        result: ReconciliationResult,
        source_tree: CanonicalTree,
        locale_tree: CanonicalTree,
        *,
        locale: str,
        authoritative_side: AuthoritativeSide,
        policy: LocaleVariationPolicy | None = None,
    ) -> LocalizationValidationResult:
        """Interpret ``result`` into a localization validation result.

        :param result: The immutable core reconciliation result.
        :param source_tree: The adapted source canonical tree.
        :param locale_tree: The adapted locale canonical tree.
        :param locale: The locale code.
        :param authoritative_side: Which tree is authoritative (REQ-008).
        :param policy: Optional locale-variation policy (REQ-103).
        :returns: An immutable :class:`LocalizationValidationResult`.
        """
        operations_by_id = {op.operation_id: op for op in result.operations.operations}
        issues = self._interpret(
            result, source_tree, locale_tree, locale=locale, policy=policy
        )
        recommendations, attachments = self._recommend.recommend(
            issues,
            authoritative_side=authoritative_side,
            operations_by_id=operations_by_id,
        )
        issues = tuple(self._attach(issue, attachments) for issue in issues)
        summary = self._summarize(issues, result)
        return LocalizationValidationResult(
            contract_version=LOCALIZATION_RESULT_CONTRACT_VERSION,
            job_id=result.job_id,
            locale=locale,
            authoritative_side=authoritative_side,
            reconciliation=result,
            issues=issues,
            recommendations=recommendations,
            summary=summary,
        )

    # -- Interpretation ----------------------------------------------------

    def _interpret(
        self,
        result: ReconciliationResult,
        source_tree: CanonicalTree,
        locale_tree: CanonicalTree,
        *,
        locale: str,
        policy: LocaleVariationPolicy | None,
    ) -> tuple[LocalizationIssue, ...]:
        move_by_source = self._move_index(result)
        issues: list[LocalizationIssue] = []
        counter = 0

        def next_id() -> str:
            nonlocal counter
            counter += 1
            return f"issue-{counter}"

        confirmed_threshold = policy.confirmed_match_threshold if policy else 0.9

        # Confirmed correspondences (skip roots to reduce noise).
        for candidate in result.match_graph.confirmed:
            s, t = candidate.source_node_ref, candidate.target_node_ref
            source_node = source_tree.nodes.get(s)
            locale_node = locale_tree.nodes.get(t)
            if source_node is None or source_node.parent_ref is None:
                continue  # skip the root correspondence

            translation_state = (
                self._translation.state_for(source_node, locale_node)
                if locale_node is not None
                else TranslationState.UNKNOWN
            )

            if s in move_by_source:
                op = move_by_source[s]
                status = LocalizationStatus.WRONG_PARENT
                op_conf: float | None = op.confidence.value
                op_ids: tuple[str, ...] = (op.operation_id,)
            elif translation_state is TranslationState.STALE:
                status = LocalizationStatus.SOURCE_UPDATED
                op_conf = None
                op_ids = ()
            elif candidate.confidence.value >= confirmed_threshold:
                status = LocalizationStatus.CONFIRMED_MATCH
                op_conf = None
                op_ids = ()
            else:
                status = LocalizationStatus.PROBABLE_MATCH
                op_conf = None
                op_ids = ()

            issues.append(
                LocalizationIssue(
                    issue_id=next_id(),
                    localization_status=status,
                    severity=_SEVERITY[status],
                    source_node_ref=s,
                    locale_node_ref=t,
                    source_node_id=_node_id(source_node),
                    locale_node_id=_node_id(locale_node),
                    source_label=_label(source_node),
                    locale_label=_label(locale_node),
                    core_match_ids=(candidate.match_id,),
                    core_operation_ids=op_ids,
                    match_confidence=candidate.confidence.value,
                    operation_confidence=op_conf,
                    translation_state=translation_state,
                    recommended_action=_ACTION.get(status, RecommendedAction.NONE),
                    message=self._message(status, source_node, locale_node),
                )
            )

        # Ambiguous correspondences (one issue per ambiguous source).
        for source_ref in sorted({c.source_node_ref for c in result.match_graph.ambiguous}):
            group = [
                c for c in result.match_graph.ambiguous if c.source_node_ref == source_ref
            ]
            source_node = source_tree.nodes.get(source_ref)
            issues.append(
                LocalizationIssue(
                    issue_id=next_id(),
                    localization_status=LocalizationStatus.AMBIGUOUS_MATCH,
                    severity=Severity.WARNING,
                    source_node_ref=source_ref,
                    source_node_id=_node_id(source_node),
                    source_label=_label(source_node),
                    core_match_ids=tuple(c.match_id for c in group),
                    match_confidence=max(c.confidence.value for c in group),
                    recommended_action=RecommendedAction.REVIEW,
                    message="multiple plausible locale correspondences require review",
                )
            )

        # Reorder is a region-level finding: one WRONG_ORDER issue per REORDER
        # operation (not one per sibling), so unmoved siblings are not flagged.
        for op in result.operations.of_type(OperationType.REORDER):
            issues.append(
                LocalizationIssue(
                    issue_id=next_id(),
                    localization_status=LocalizationStatus.WRONG_ORDER,
                    severity=Severity.WARNING,
                    source_node_ref=op.source_node_refs[0] if op.source_node_refs else None,
                    core_operation_ids=(op.operation_id,),
                    core_match_ids=op.match_ids,
                    operation_confidence=op.confidence.value,
                    recommended_action=RecommendedAction.REORDER,
                    message="matched siblings appear in a different order under a matched parent",
                )
            )

        # Missing (source-only DELETE) and extra (locale-only INSERT) nodes.
        for op in result.operations.operations:
            if op.type is OperationType.DELETE and op.source_node_refs:
                s = op.source_node_refs[0]
                issues.append(
                    self._presence_issue(
                        next_id(), op, source_tree, locale_tree,
                        node_ref=s, on_source=True, locale=locale, policy=policy,
                        default_status=LocalizationStatus.MISSING_IN_LOCALE,
                    )
                )
            elif op.type is OperationType.INSERT and op.target_node_refs:
                t = op.target_node_refs[0]
                issues.append(
                    self._presence_issue(
                        next_id(), op, source_tree, locale_tree,
                        node_ref=t, on_source=False, locale=locale, policy=policy,
                        default_status=LocalizationStatus.EXTRA_IN_LOCALE,
                    )
                )

        # Identifier conflicts surfaced by the core (REQ-100, AC-010).
        for diagnostic in result.diagnostics:
            if diagnostic.code == "DUPLICATE_PERSISTENT_ID":
                issues.append(
                    LocalizationIssue(
                        issue_id=next_id(),
                        localization_status=LocalizationStatus.IDENTIFIER_CONFLICT,
                        severity=Severity.ERROR,
                        message="duplicate persistent identifier detected; identity is ambiguous",
                    )
                )

        return self._without_contradictory_presence(tuple(issues), result)

    @staticmethod
    def _without_contradictory_presence(
        issues: tuple[LocalizationIssue, ...], result: ReconciliationResult
    ) -> tuple[LocalizationIssue, ...]:
        """Drop presence statuses that contradict an ambiguity (REQ-058, REQ-090).

        Ambiguous correspondence dominates conflicting presence statuses: a node
        held in an unresolved correspondence must never be reported as
        ``MISSING_IN_LOCALE`` or ``EXTRA_IN_LOCALE`` as well, because that
        inflates one uncertainty into several confident-looking defects.

        The core already withholds those operations (REQ-058), so this normally
        filters nothing. It is the second barrier: it also holds for a result
        produced by an injected classifier or by the ``EMIT_ALL`` presence
        policy. Those forced operations remain visible in the referenced core
        result, which this layer never modifies (REQ-176).
        """
        ambiguous_sources = {
            c.source_node_ref for c in result.match_graph.ambiguous
        } | result.alignment.unresolved_source_refs
        ambiguous_targets = {
            c.target_node_ref for c in result.match_graph.ambiguous
        } | result.alignment.unresolved_target_refs
        kept: list[LocalizationIssue] = []
        for issue in issues:
            status = issue.localization_status
            if (
                status is LocalizationStatus.MISSING_IN_LOCALE
                and issue.source_node_ref in ambiguous_sources
            ):
                continue
            if (
                status is LocalizationStatus.EXTRA_IN_LOCALE
                and issue.locale_node_ref in ambiguous_targets
            ):
                continue
            kept.append(issue)
        return tuple(kept)

    def _presence_issue(
        self,
        issue_id: str,
        op: StructuralOperation,
        source_tree: CanonicalTree,
        locale_tree: CanonicalTree,
        *,
        node_ref: NodeRef,
        on_source: bool,
        locale: str,
        policy: LocaleVariationPolicy | None,
        default_status: LocalizationStatus,
    ) -> LocalizationIssue:
        node = (source_tree if on_source else locale_tree).nodes.get(node_ref)
        node_type = node.node_type if node is not None else ""
        exemption = self._policy.exemption_for(
            policy, locale=locale, operation=op.type, node_type=node_type
        )
        status = (
            LocalizationStatus.EXEMPT_LOCALE_VARIATION if exemption else default_status
        )
        return LocalizationIssue(
            issue_id=issue_id,
            localization_status=status,
            severity=_SEVERITY[status],
            source_node_ref=node_ref if on_source else None,
            locale_node_ref=None if on_source else node_ref,
            source_node_id=_node_id(node) if on_source else None,
            locale_node_id=None if on_source else _node_id(node),
            source_label=_label(node) if on_source else None,
            locale_label=None if on_source else _label(node),
            core_operation_ids=(op.operation_id,),
            operation_confidence=op.confidence.value,
            recommended_action=_ACTION.get(status, RecommendedAction.NONE),
            policy_exemption=exemption,
            message=f"policy-exempt variation ({exemption})" if exemption else None,
        )

    @staticmethod
    def _move_index(
        result: ReconciliationResult,
    ) -> dict[NodeRef, StructuralOperation]:
        moves: dict[NodeRef, StructuralOperation] = {}
        for op in result.operations.of_type(OperationType.MOVE):
            for ref in op.source_node_refs:
                moves[ref] = op
        return moves

    @staticmethod
    def _message(
        status: LocalizationStatus,
        source_node: CanonicalNode | None,
        locale_node: CanonicalNode | None,
    ) -> str | None:
        if status is LocalizationStatus.WRONG_PARENT:
            return "corresponding node appears under an incompatible parent"
        if status is LocalizationStatus.WRONG_ORDER:
            return "matched siblings appear in a different order"
        if status is LocalizationStatus.SOURCE_UPDATED:
            return "source changed after the locale was last synchronized"
        return None

    # -- Attachment & summary ---------------------------------------------

    @staticmethod
    def _attach(
        issue: LocalizationIssue, attachments: dict[str, tuple[str, float]]
    ) -> LocalizationIssue:
        link = attachments.get(issue.issue_id)
        if link is None:
            return issue
        recommendation_id, repair_confidence = link
        return issue.model_copy(
            update={
                "recommendation_id": recommendation_id,
                "repair_confidence": repair_confidence,
            }
        )

    @staticmethod
    def _summarize(
        issues: tuple[LocalizationIssue, ...], result: ReconciliationResult
    ) -> LocalizationSummary:
        status_counts: dict[str, int] = {}
        action_counts: dict[str, int] = {}
        for issue in issues:
            status_counts[issue.localization_status.value] = (
                status_counts.get(issue.localization_status.value, 0) + 1
            )
            action_counts[issue.recommended_action.value] = (
                action_counts.get(issue.recommended_action.value, 0) + 1
            )
        operation_counts: dict[str, int] = {}
        for op in result.operations.operations:
            operation_counts[op.type.value] = operation_counts.get(op.type.value, 0) + 1

        def count(status: LocalizationStatus) -> int:
            return status_counts.get(status.value, 0)

        node_counts = NodeCounts(
            confirmed=count(LocalizationStatus.CONFIRMED_MATCH),
            probable=count(LocalizationStatus.PROBABLE_MATCH),
            ambiguous=count(LocalizationStatus.AMBIGUOUS_MATCH),
            missing=count(LocalizationStatus.MISSING_IN_LOCALE),
            extra=count(LocalizationStatus.EXTRA_IN_LOCALE),
            structurally_divergent=(
                count(LocalizationStatus.WRONG_PARENT)
                + count(LocalizationStatus.WRONG_ORDER)
                + count(LocalizationStatus.LOCALE_DIVERGED)
            ),
            exempt=count(LocalizationStatus.EXEMPT_LOCALE_VARIATION),
        )
        return LocalizationSummary(
            status_counts=status_counts,
            operation_counts=operation_counts,
            action_counts=action_counts,
            node_counts=node_counts,
            direct_issue_count=len(issues),
            suppressed_effect_count=len(result.suppression.suppressed_effects),
            unresolved_region_count=len(result.alignment.unresolved_region_ids),
        )
