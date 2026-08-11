"""Stage-metric accumulation and resource-limit checks (REQ-196-200).

A :class:`StageTimer` accumulates per-stage timings and counts. Resource-limit
checks raise :class:`ResourceLimitExceededError` (or, when the execution
context requests it, let the engine mark the result explicitly incomplete).
Node/depth limits are checked *before* the expensive stages run.
"""

from __future__ import annotations

import time

from reconciliation.core.contracts.commands import ResourceLimits
from reconciliation.core.contracts.diagnostics import PipelineStage
from reconciliation.core.contracts.metrics import ReconciliationMetrics, StageMetric
from reconciliation.core.contracts.tree import CanonicalTree
from reconciliation.core.errors import ResourceLimitExceededError


def tree_depth(tree: CanonicalTree) -> int:
    """Return the maximum depth of ``tree`` (root depth = 1)."""
    depth = 0
    stack = [(tree.root_node_ref, 1)]
    while stack:
        node_ref, d = stack.pop()
        depth = max(depth, d)
        for child in tree.nodes[node_ref].child_refs:
            stack.append((child, d + 1))
    return depth


def check_pre_limits(
    source: CanonicalTree,
    target: CanonicalTree,
    limits: ResourceLimits,
    *,
    correlation_id: str | None = None,
) -> None:
    """Check node-count and depth limits before matching begins (REQ-196).

    :raises ResourceLimitExceededError: If a configured limit is exceeded.
    """
    total_nodes = len(source.nodes) + len(target.nodes)
    if limits.max_node_count is not None and total_nodes > limits.max_node_count:
        raise ResourceLimitExceededError(
            "combined node count exceeds configured limit",
            correlation_id=correlation_id,
            context={"total_nodes": total_nodes, "limit": limits.max_node_count},
        )
    if limits.max_tree_depth is not None:
        deepest = max(tree_depth(source), tree_depth(target))
        if deepest > limits.max_tree_depth:
            raise ResourceLimitExceededError(
                "tree depth exceeds configured limit",
                correlation_id=correlation_id,
                context={"depth": deepest, "limit": limits.max_tree_depth},
            )


class StageTimer:
    """Accumulates per-stage timing and counts for a run."""

    def __init__(self, source_node_count: int, target_node_count: int) -> None:
        self._source = source_node_count
        self._target = target_node_count
        self._metrics: list[StageMetric] = []

    def record(
        self,
        stage: PipelineStage,
        start: float,
        *,
        candidate_count: int = 0,
        result_count: int = 0,
    ) -> None:
        """Record a completed stage given its ``start`` from :func:`time.perf_counter`."""
        self._metrics.append(
            StageMetric(
                stage=stage,
                duration_ms=round((time.perf_counter() - start) * 1000.0, 6),
                candidate_count=candidate_count,
                result_count=result_count,
            )
        )

    def build(self) -> ReconciliationMetrics:
        """Return the accumulated metrics."""
        return ReconciliationMetrics(
            source_node_count=self._source,
            target_node_count=self._target,
            stage_metrics=tuple(self._metrics),
        )
