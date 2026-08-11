"""Observability report contract (REQ-243-246).

Exposes the counts and stage timings for a comparison and, crucially,
distinguishes a *technical failure* from a *completed comparison that contains
validation issues* (REQ-246) — the two must never be conflated in metrics.
"""

from __future__ import annotations

from pydantic import Field

from reconciliation.core.contracts.base import StrictModel


class ObservabilityReport(StrictModel):
    """Counts, timings, and outcome classification for one comparison.

    :ivar job_id: The comparison job.
    :ivar correlation_id: Tracing identifier (REQ-245).
    :ivar outcome: ``COMPLETED``, ``REJECTED``, or ``FAILED``.
    :ivar technical_failure: True for REJECTED/FAILED (REQ-246).
    :ivar completed_with_issues: True when the comparison completed but reported
        blocking/validation issues (REQ-246).
    :ivar source_node_count: Source node count.
    :ivar target_node_count: Target node count.
    :ivar candidate_count: Match candidates generated (REQ-244).
    :ivar match_count: Confirmed matches.
    :ivar ambiguity_count: Ambiguous matches.
    :ivar operation_count: Structural operations.
    :ivar suppression_count: Suppressed effects.
    :ivar recommendation_count: Repair recommendations.
    :ivar stage_durations_ms: Per-stage durations (REQ-199, REQ-243).
    """

    job_id: str
    correlation_id: str | None = None
    outcome: str
    technical_failure: bool
    completed_with_issues: bool = False
    source_node_count: int = 0
    target_node_count: int = 0
    candidate_count: int = 0
    match_count: int = 0
    ambiguity_count: int = 0
    operation_count: int = 0
    suppression_count: int = 0
    recommendation_count: int = 0
    stage_durations_ms: dict[str, float] = Field(default_factory=dict)
