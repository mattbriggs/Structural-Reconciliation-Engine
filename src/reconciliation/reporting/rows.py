"""Builds report rows from a localization result (REQ-150, REQ-151).

Produces one row per localization issue and, when requested, one row per
suppressed effect (REQ-088). Rows are enriched with source/locale paths and
revisions when the canonical trees are supplied. Content can be redacted for
sharing (REQ-221, REQ-226). Row order is deterministic.
"""

from __future__ import annotations

from reconciliation.application.contracts.localization import LocalizationValidationResult
from reconciliation.application.contracts.reviews import DecisionType, ReviewerDecision
from reconciliation.core.contracts.matches import MatchCandidate
from reconciliation.core.contracts.tree import CanonicalNode, CanonicalTree, NodeRef
from reconciliation.reporting.contracts import ReportOptions, ReportRow, ReportTable
from reconciliation.version import REPORT_CONTRACT_VERSION

_REDACTED = "[redacted]"


def _node(tree: CanonicalTree | None, ref: NodeRef | None) -> CanonicalNode | None:
    if tree is None or ref is None:
        return None
    return tree.nodes.get(ref)


def _path(node: CanonicalNode | None) -> str | None:
    if node is None or node.source_location is None:
        return None
    return node.source_location.xpath


def _revision(node: CanonicalNode | None, *keys: str) -> str | None:
    if node is None:
        return None
    for key in keys:
        value = node.content_properties.get(key) or node.identity_properties.get(key)
        if value is not None:
            return str(value)
    return None


def _decision_cell(decision: ReviewerDecision) -> str:
    """Render a reviewer decision for the report cell, preserving the override.

    For an override the original engine status stays in ``localization_status``;
    this cell records the reviewer's disposition and replacement (AC-030).
    """
    if decision.decision is DecisionType.OVERRIDE and decision.overridden_status:
        return f"OVERRIDE->{decision.overridden_status}"
    return decision.decision.value


def build_report_table(
    result: LocalizationValidationResult,
    *,
    source_tree: CanonicalTree | None = None,
    locale_tree: CanonicalTree | None = None,
    options: ReportOptions | None = None,
    reviewer_decisions: tuple[ReviewerDecision, ...] = (),
) -> ReportTable:
    """Flatten a localization result into a versioned report table.

    :param result: The immutable localization validation result.
    :param source_tree: Source canonical tree, for paths/revisions (optional).
    :param locale_tree: Locale canonical tree, for paths/revisions (optional).
    :param options: Report options; defaults to including suppressed rows.
    :param reviewer_decisions: Decisions to surface in the ``reviewer_decision``
        column; the engine's original status is retained (REQ-131, AC-030).
    :returns: A :class:`ReportTable`.
    """
    opts = options or ReportOptions()
    reconciliation = result.reconciliation
    decision_by_issue = {d.issue_id: d for d in reviewer_decisions}
    matches_by_id = {c.match_id: c for c in reconciliation.match_graph.candidates}
    suppression_counts_by_root: dict[str, int] = {}
    for effect in reconciliation.suppression.suppressed_effects:
        suppression_counts_by_root[effect.root_operation_id] = (
            suppression_counts_by_root.get(effect.root_operation_id, 0) + 1
        )

    rows: list[ReportRow] = []
    for issue in result.issues:
        source_node = _node(source_tree, issue.source_node_ref)
        locale_node = _node(locale_tree, issue.locale_node_ref)
        root_operation_id = issue.core_operation_ids[0] if issue.core_operation_ids else None
        primary_node = source_node or locale_node
        rows.append(
            ReportRow(
                job_id=result.job_id,
                result_id=issue.issue_id,
                source_node_id=issue.source_node_id,
                locale_node_id=issue.locale_node_id,
                source_path=_path(source_node),
                locale_path=_path(locale_node),
                node_type=primary_node.node_type if primary_node is not None else None,
                source_label=_maybe_redact(issue.source_label, opts),
                locale_label=_maybe_redact(issue.locale_label, opts),
                match_status=_match_status(issue.core_match_ids, matches_by_id),
                localization_status=issue.localization_status.value,
                operation=_operation_type(root_operation_id, reconciliation),
                match_confidence=issue.match_confidence,
                operation_confidence=issue.operation_confidence,
                repair_confidence=issue.repair_confidence,
                evidence_codes=_evidence_codes(issue.core_match_ids, matches_by_id),
                source_revision=_revision(source_node, "revision"),
                locale_revision=_revision(locale_node, "revision", "source-revision"),
                root_operation_id=root_operation_id,
                is_suppressed=False,
                suppressed_effect_count=sum(
                    suppression_counts_by_root.get(op_id, 0)
                    for op_id in issue.core_operation_ids
                ),
                recommended_action=issue.recommended_action.value,
                auto_fix_eligible=issue.auto_fix_eligible,
                reviewer_decision=(
                    _decision_cell(decision_by_issue[issue.issue_id])
                    if issue.issue_id in decision_by_issue
                    else None
                ),
                policy_exemption=issue.policy_exemption,
                message=_maybe_redact(issue.message, opts),
            )
        )

    if opts.include_suppressed:
        for index, effect in enumerate(reconciliation.suppression.suppressed_effects, start=1):
            rows.append(
                ReportRow(
                    job_id=result.job_id,
                    result_id=f"suppressed-{index}",
                    localization_status="SUPPRESSED_EFFECT",
                    operation=effect.category,
                    root_operation_id=effect.root_operation_id,
                    is_suppressed=True,
                    suppression_rule=effect.suppression_rule_id,
                    operation_confidence=effect.confidence.value,
                    message=f"derived effect suppressed by {effect.root_operation_id}",
                )
            )

    return ReportTable(
        schema_version=REPORT_CONTRACT_VERSION,
        job_id=result.job_id,
        rows=tuple(rows),
    )


def _maybe_redact(value: str | None, options: ReportOptions) -> str | None:
    if value is None:
        return None
    return _REDACTED if options.redact_content else value


def _match_status(
    match_ids: tuple[str, ...], matches_by_id: dict[str, MatchCandidate]
) -> str | None:
    for match_id in match_ids:
        candidate = matches_by_id.get(match_id)
        if candidate is not None:
            return candidate.state.value
    return None


def _evidence_codes(
    match_ids: tuple[str, ...], matches_by_id: dict[str, MatchCandidate]
) -> tuple[str, ...]:
    codes: list[str] = []
    for match_id in match_ids:
        candidate = matches_by_id.get(match_id)
        if candidate is None:
            continue
        for evidence in candidate.evidence:
            if evidence.code.value not in codes:
                codes.append(evidence.code.value)
    return tuple(codes)


def _operation_type(operation_id: str | None, reconciliation: object) -> str | None:
    if operation_id is None:
        return None
    from reconciliation.core.contracts.results import ReconciliationResult

    assert isinstance(reconciliation, ReconciliationResult)
    for op in reconciliation.operations.operations:
        if op.operation_id == operation_id:
            return op.type.value
    return None
