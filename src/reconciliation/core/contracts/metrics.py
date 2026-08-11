"""Reconciliation metrics contracts (REQ-199, REQ-244).

Metrics expose per-stage timings and counts so callers can observe engine
behavior and enforce resource policy. Timings are excluded from determinism
comparisons (they are volatile); counts are deterministic (REQ-202).
"""

from __future__ import annotations

from pydantic import Field

from reconciliation.core.contracts.base import StrictModel
from reconciliation.core.contracts.diagnostics import PipelineStage


class StageMetric(StrictModel):
    """Timing and counts for one pipeline stage.

    :ivar stage: The pipeline stage.
    :ivar duration_ms: Wall-clock duration in milliseconds (volatile).
    :ivar candidate_count: Candidates considered in this stage.
    :ivar result_count: Records produced by this stage.
    """

    stage: PipelineStage
    duration_ms: float = Field(ge=0.0)
    candidate_count: int = Field(default=0, ge=0)
    result_count: int = Field(default=0, ge=0)


class ReconciliationMetrics(StrictModel):
    """Aggregate metrics for a reconciliation run.

    :ivar source_node_count: Number of source nodes.
    :ivar target_node_count: Number of target nodes.
    :ivar stage_metrics: Per-stage metrics in pipeline order.

    .. note::
       :meth:`deterministic_fingerprint` intentionally excludes ``duration_ms``
       so that determinism tests (AC-012) compare only stable quantities.
    """

    source_node_count: int = Field(ge=0)
    target_node_count: int = Field(ge=0)
    stage_metrics: tuple[StageMetric, ...] = ()

    def deterministic_fingerprint(self) -> dict[str, int]:
        """Return the stable, timing-free portion of the metrics."""
        fingerprint = {
            "source_node_count": self.source_node_count,
            "target_node_count": self.target_node_count,
        }
        for metric in self.stage_metrics:
            fingerprint[f"{metric.stage.value}.candidate_count"] = metric.candidate_count
            fingerprint[f"{metric.stage.value}.result_count"] = metric.result_count
        return fingerprint
