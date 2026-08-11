"""Quality benchmark against the labeled corpus (SRS §9.7, REQ-191-195).

Asserts structural correctness on unambiguous labeled cases (precision/recall
== 1.0 per operation) and that ambiguity is preserved on repeated structure.
These are correctness checks on a known corpus, not production thresholds.
"""

from __future__ import annotations

from reconciliation.benchmark.corpus import ambiguous_cases, clean_cases
from reconciliation.benchmark.evaluator import evaluate_quality


def test_clean_corpus_is_perfectly_reconciled() -> None:
    metrics = evaluate_quality(clean_cases())
    assert metrics.cases_evaluated == 5
    assert metrics.match_precision == 1.0
    assert metrics.match_recall == 1.0
    assert metrics.deterministic_consistency is True
    for score in metrics.operation_scores:
        assert score.precision == 1.0, score.operation_type
        assert score.recall == 1.0, score.operation_type


def test_all_core_operations_are_exercised() -> None:
    metrics = evaluate_quality(clean_cases())
    exercised = {s.operation_type for s in metrics.operation_scores}
    assert {"INSERT", "DELETE", "UPDATE", "MOVE", "REORDER"} <= exercised


def test_ambiguous_corpus_preserves_ambiguity() -> None:
    metrics = evaluate_quality(ambiguous_cases())
    # Repeated indistinguishable nodes are reported ambiguous, not forced.
    assert metrics.ambiguity_rate > 0.0
    assert metrics.deterministic_consistency is True


def test_operation_score_precision_recall_math() -> None:
    from reconciliation.benchmark.contracts import OperationScore

    score = OperationScore(
        operation_type="MOVE", true_positives=3, false_positives=1, false_negatives=1
    )
    assert score.precision == 0.75
    assert score.recall == 0.75
    # Empty score defaults to 1.0 (no predictions, no expectations).
    assert OperationScore(operation_type="X").precision == 1.0
