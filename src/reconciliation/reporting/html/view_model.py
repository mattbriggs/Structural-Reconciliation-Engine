"""HTML report view model (REQ-137, REQ-240, REQ-241, REQ-242).

Transforms the immutable localization result and flattened report table into a
presentation-only view model. Confidence is rendered with a textual band as
well as its number (REQ-240); status carries a non-color textual symbol
(REQ-239); ambiguous findings are explicitly marked as requiring human review
(REQ-242); and root-cause summaries precede detailed consequences (REQ-241).

The view model contains no callables and never mutates the result — the report
is a read-only projection (report state is client-side only).
"""

from __future__ import annotations

from typing import Any

from reconciliation.application.contracts.localization import LocalizationValidationResult
from reconciliation.reporting.contracts import ReportTable

#: Non-color textual symbols for statuses (REQ-239).
_STATUS_SYMBOL: dict[str, str] = {
    "CONFIRMED_MATCH": "OK",
    "PROBABLE_MATCH": "~",
    "AMBIGUOUS_MATCH": "?",
    "MISSING_IN_LOCALE": "-",
    "EXTRA_IN_LOCALE": "+",
    "WRONG_PARENT": "!",
    "WRONG_ORDER": "><",
    "MOVED": ">",
    "SOURCE_UPDATED": "*",
    "LOCALE_DIVERGED": "!",
    "IDENTIFIER_CONFLICT": "!!",
    "EXEMPT_LOCALE_VARIATION": "=",
    "SUPPRESSED_EFFECT": ".",
}

_REVIEW_STATUSES = {"AMBIGUOUS_MATCH"}


def confidence_text(value: float | None) -> str:
    """Return a textual confidence interpretation plus its number (REQ-240).

    :param value: A confidence in ``[0, 1]`` or ``None``.
    :returns: e.g. ``"high (0.91)"`` or ``"—"`` when absent. Values are
        uncalibrated scores, described qualitatively for readers.
    """
    if value is None:
        return "—"
    if value >= 0.8:
        band = "high"
    elif value >= 0.5:
        band = "medium"
    else:
        band = "low"
    return f"{band} ({value:.2f})"


def build_view_model(
    result: LocalizationValidationResult, table: ReportTable
) -> dict[str, Any]:
    """Build the presentation view model for the HTML template.

    :param result: The localization validation result.
    :param table: The flattened report table (source of row data).
    :returns: A JSON-serializable mapping consumed by the Jinja2 template.
    """
    reconciliation = result.reconciliation
    operations_by_id = {op.operation_id: op for op in reconciliation.operations.operations}

    issue_rows = [row for row in table.rows if not row.is_suppressed]
    suppressed_rows = [row for row in table.rows if row.is_suppressed]

    issues = [_issue_view(row) for row in issue_rows]

    # Root-cause summaries first (REQ-241): the operations designated as roots.
    root_causes = []
    for op_id in reconciliation.causality.selected.root_operation_ids:
        op = operations_by_id.get(op_id)
        if op is None:
            continue
        root_causes.append(
            {
                "operation_id": op.operation_id,
                "type": op.type.value,
                "confidence": confidence_text(op.confidence.value),
                "evidence_codes": list(op.evidence_codes),
            }
        )

    recommendations = [
        {
            "recommendation_id": rec.recommendation_id,
            "operation": rec.operation.value,
            "issue_id": rec.issue_id,
            "authoritative_side": rec.authoritative_side.value,
            "target_side": rec.target_side.value,
            "repair_confidence": confidence_text(rec.repair_confidence),
            "executable": rec.executable,
            "changes": sorted(change.value for change in rec.changes),
            "preconditions": list(rec.preconditions),
            "postconditions": list(rec.postconditions),
        }
        for rec in result.recommendations
    ]

    return {
        "job_id": result.job_id,
        "locale": result.locale,
        "authoritative_side": result.authoritative_side.value,
        "versions": reconciliation.profile_versions.model_dump(mode="json"),
        "summary": {
            "status_counts": result.summary.status_counts,
            "node_counts": result.summary.node_counts.model_dump(mode="json"),
            "direct_issue_count": result.summary.direct_issue_count,
            "suppressed_effect_count": result.summary.suppressed_effect_count,
            "unresolved_region_count": result.summary.unresolved_region_count,
        },
        "root_causes": root_causes,
        "issues": issues,
        "suppressed": [_suppressed_view(row) for row in suppressed_rows],
        "recommendations": recommendations,
    }


def _issue_view(row: Any) -> dict[str, Any]:
    status = row.localization_status or ""
    return {
        "result_id": row.result_id,
        "status": status,
        "status_symbol": _STATUS_SYMBOL.get(status, "?"),
        "needs_review": status in _REVIEW_STATUSES,
        "source_node_id": row.source_node_id,
        "locale_node_id": row.locale_node_id,
        "source_path": row.source_path,
        "locale_path": row.locale_path,
        "node_type": row.node_type,
        "source_label": row.source_label,
        "locale_label": row.locale_label,
        "match_status": row.match_status,
        "match_confidence": confidence_text(row.match_confidence),
        "operation_confidence": confidence_text(row.operation_confidence),
        "repair_confidence": confidence_text(row.repair_confidence),
        "evidence_codes": list(row.evidence_codes),
        "recommended_action": row.recommended_action,
        "policy_exemption": row.policy_exemption,
        "message": row.message,
    }


def _suppressed_view(row: Any) -> dict[str, Any]:
    return {
        "result_id": row.result_id,
        "category": row.operation,
        "root_operation_id": row.root_operation_id,
        "suppression_rule": row.suppression_rule,
        "confidence": confidence_text(row.operation_confidence),
        "message": row.message,
    }
