"""Observability report builder (REQ-243-246).

Derives an :class:`ObservabilityReport` from a job record and (optional)
localization result. All values are counts/timings — never content — so the
report is safe to log by default (REQ-243).
"""

from __future__ import annotations

from reconciliation.application.contracts.jobs import ComparisonState, JobRecord
from reconciliation.application.contracts.localization import LocalizationValidationResult
from reconciliation.application.contracts.observability import ObservabilityReport
from reconciliation.core.contracts.diagnostics import Severity


def build_observability_report(
    record: JobRecord, result: LocalizationValidationResult | None
) -> ObservabilityReport:
    """Build an observability report from a job outcome.

    :param record: The job lifecycle record.
    :param result: The localization result when completed, else ``None``.
    :returns: An :class:`ObservabilityReport`.
    """
    technical_failure = record.state in (ComparisonState.REJECTED, ComparisonState.FAILED)
    if result is None:
        return ObservabilityReport(
            job_id=record.job_id,
            correlation_id=record.correlation_id,
            outcome=record.state.value,
            technical_failure=technical_failure,
        )

    reconciliation = result.reconciliation
    metrics = reconciliation.metrics
    candidate_count = sum(m.candidate_count for m in metrics.stage_metrics)
    has_blocking = any(issue.severity is Severity.ERROR for issue in result.issues)

    return ObservabilityReport(
        job_id=record.job_id,
        correlation_id=record.correlation_id,
        outcome=record.state.value,
        technical_failure=False,
        completed_with_issues=has_blocking,
        source_node_count=metrics.source_node_count,
        target_node_count=metrics.target_node_count,
        candidate_count=candidate_count,
        match_count=len(reconciliation.match_graph.confirmed),
        ambiguity_count=len(reconciliation.match_graph.ambiguous),
        operation_count=len(reconciliation.operations.operations),
        suppression_count=len(reconciliation.suppression.suppressed_effects),
        recommendation_count=len(result.recommendations),
        stage_durations_ms={
            m.stage.value: m.duration_ms for m in metrics.stage_metrics
        },
    )
