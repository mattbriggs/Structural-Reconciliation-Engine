"""Quality and performance evaluation (SRS §9.7, REQ-191-195).

Runs the reconciliation engine over labeled cases and computes operation and
match precision/recall, ambiguity rate, and deterministic consistency. Also
captures reproducible performance records (timing, candidate counts, peak
memory). No production thresholds are declared here — metrics are measured and
returned for reporting.
"""

from __future__ import annotations

import time
import tracemalloc
from functools import lru_cache

from reconciliation.benchmark.contracts import (
    ExpectedOperation,
    LabeledCase,
    OperationScore,
    PerformanceRecord,
    QualityMetrics,
)
from reconciliation.core.contracts.commands import ExecutionContext, ReconcileTreesCommand
from reconciliation.core.contracts.profiles import OperationType
from reconciliation.core.contracts.results import ReconciliationResult
from reconciliation.core.contracts.tree import CanonicalTree, NodeRef
from reconciliation.core.engine import DefaultReconciliationEngine
from reconciliation.profiles import ProfileBundle, load_named_bundle


@lru_cache
def _bundle() -> ProfileBundle:
    return load_named_bundle("dita_map_v1")


def reconcile_trees(
    source: CanonicalTree, target: CanonicalTree, *, job_id: str = "bench"
) -> ReconciliationResult:
    """Reconcile two trees with the reference DITA profile bundle."""
    bundle = _bundle()
    return DefaultReconciliationEngine().reconcile(
        ReconcileTreesCommand(
            source_tree=source,
            target_tree=target,
            normalization_profile=bundle.normalization,
            matching_profile=bundle.matching,
            alignment_profile=bundle.alignment,
            operation_profile=bundle.operation,
            suppression_profile=bundle.suppression,
            execution_context=ExecutionContext(job_id=job_id),
        )
    )


def _cid(tree: CanonicalTree, ref: NodeRef) -> str:
    value = tree.nodes[ref].identity_properties.get("id")
    return str(value) if value is not None else ref


def _predicted_operations(
    result: ReconciliationResult, source: CanonicalTree, target: CanonicalTree
) -> set[ExpectedOperation]:
    predicted: set[ExpectedOperation] = set()
    for op in result.operations.operations:
        if op.type is OperationType.MATCH:
            continue
        predicted.add(
            ExpectedOperation(
                operation_type=op.type,
                source_ids=frozenset(_cid(source, r) for r in op.source_node_refs),
                target_ids=frozenset(_cid(target, r) for r in op.target_node_refs),
            )
        )
    return predicted


def evaluate_quality(cases: tuple[LabeledCase, ...]) -> QualityMetrics:
    """Evaluate the engine over a labeled corpus and return quality metrics."""
    scores: dict[str, OperationScore] = {}
    match_tp = match_fp = match_fn = 0
    ambiguous_sources = 0
    total_sources = 0
    deterministic = True
    start = time.perf_counter()

    def score(op_type: str) -> OperationScore:
        return scores.setdefault(op_type, OperationScore(operation_type=op_type))

    for case in cases:
        result = reconcile_trees(case.source_tree, case.target_tree, job_id=case.case_id)
        again = reconcile_trees(case.source_tree, case.target_tree, job_id=case.case_id)
        if result.deterministic_fingerprint() != again.deterministic_fingerprint():
            deterministic = False

        # Matches (confirmed pairs with canonical ids on both sides).
        predicted_matches = {
            (_cid(case.source_tree, c.source_node_ref), _cid(case.target_tree, c.target_node_ref))
            for c in result.match_graph.confirmed
            if case.source_tree.nodes[c.source_node_ref].identity_properties.get("id")
            and case.target_tree.nodes[c.target_node_ref].identity_properties.get("id")
        }
        expected_matches = set(case.expected_matches)
        match_tp += len(predicted_matches & expected_matches)
        match_fp += len(predicted_matches - expected_matches)
        match_fn += len(expected_matches - predicted_matches)

        # Operations.
        predicted_ops = _predicted_operations(result, case.source_tree, case.target_tree)
        expected_ops = set(case.expected_operations)
        for op_type in {o.operation_type.value for o in predicted_ops | expected_ops}:
            s = score(op_type)
            pred = {o for o in predicted_ops if o.operation_type.value == op_type}
            exp = {o for o in expected_ops if o.operation_type.value == op_type}
            scores[op_type] = s.model_copy(
                update={
                    "true_positives": s.true_positives + len(pred & exp),
                    "false_positives": s.false_positives + len(pred - exp),
                    "false_negatives": s.false_negatives + len(exp - pred),
                }
            )

        # Ambiguity.
        total_sources += sum(
            1 for ref in case.source_tree.nodes if case.source_tree.nodes[ref].parent_ref
        )
        ambiguous_sources += len({c.source_node_ref for c in result.match_graph.ambiguous})

    runtime_ms = round((time.perf_counter() - start) * 1000.0, 3)
    return QualityMetrics(
        cases_evaluated=len(cases),
        match_precision=match_tp / (match_tp + match_fp) if (match_tp + match_fp) else 1.0,
        match_recall=match_tp / (match_tp + match_fn) if (match_tp + match_fn) else 1.0,
        operation_scores=tuple(scores[k] for k in sorted(scores)),
        ambiguity_rate=round(ambiguous_sources / total_sources, 6) if total_sources else 0.0,
        deterministic_consistency=deterministic,
        total_runtime_ms=runtime_ms,
    )


def measure_performance(
    scenario: str, source: CanonicalTree, target: CanonicalTree
) -> PerformanceRecord:
    """Reconcile a pair and capture a reproducible performance record."""
    tracemalloc.start()
    start = time.perf_counter()
    result = reconcile_trees(source, target, job_id=scenario)
    duration_ms = round((time.perf_counter() - start) * 1000.0, 3)
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    candidate_count = sum(m.candidate_count for m in result.metrics.stage_metrics)
    return PerformanceRecord(
        scenario=scenario,
        source_node_count=len(source.nodes),
        target_node_count=len(target.nodes),
        duration_ms=duration_ms,
        candidate_count=candidate_count,
        peak_memory_kb=round(peak / 1024.0, 3),
        match_count=len(result.match_graph.confirmed),
        operation_count=len(result.operations.operations),
    )
