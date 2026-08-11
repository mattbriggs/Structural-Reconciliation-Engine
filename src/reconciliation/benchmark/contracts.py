"""Benchmark contracts: labeled cases, quality metrics, performance records.

Expected operations and matches are keyed by *canonical identity* (the ``id``
property) rather than runtime node references, so a labeled case is independent
of how a tree is built.
"""

from __future__ import annotations

from pydantic import Field

from reconciliation.core.contracts.base import StrictModel
from reconciliation.core.contracts.profiles import OperationType
from reconciliation.core.contracts.tree import CanonicalTree


class ExpectedOperation(StrictModel):
    """An expected structural operation, keyed by canonical node ids."""

    operation_type: OperationType
    source_ids: frozenset[str] = frozenset()
    target_ids: frozenset[str] = frozenset()


class LabeledCase(StrictModel):
    """A labeled reconciliation case for quality evaluation.

    :ivar case_id: Stable identifier.
    :ivar category: Corpus category (e.g. ``isolated_insertion``).
    :ivar source_tree: The source canonical tree.
    :ivar target_tree: The target canonical tree.
    :ivar expected_operations: The operations a correct engine should report,
        excluding ``MATCH`` (which is verified via expected matches).
    :ivar expected_matches: Expected confirmed (source_id, target_id) pairs.
    :ivar expected_ambiguous_source_ids: Source ids that should be ambiguous.
    """

    case_id: str
    category: str
    source_tree: CanonicalTree
    target_tree: CanonicalTree
    expected_operations: tuple[ExpectedOperation, ...] = ()
    expected_matches: tuple[tuple[str, str], ...] = ()
    expected_ambiguous_source_ids: frozenset[str] = frozenset()


class OperationScore(StrictModel):
    """Precision/recall for one operation type."""

    operation_type: str
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom else 1.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom else 1.0


class QualityMetrics(StrictModel):
    """Aggregate quality metrics over a labeled corpus (SRS §9.7)."""

    cases_evaluated: int
    match_precision: float
    match_recall: float
    operation_scores: tuple[OperationScore, ...] = ()
    ambiguity_rate: float = 0.0
    deterministic_consistency: bool = True
    total_runtime_ms: float = 0.0

    def score_for(self, operation_type: str) -> OperationScore | None:
        """Return the score for an operation type, if present."""
        for score in self.operation_scores:
            if score.operation_type == operation_type:
                return score
        return None


class PerformanceRecord(StrictModel):
    """A reproducible performance measurement for one scenario."""

    scenario: str
    source_node_count: int
    target_node_count: int
    duration_ms: float = Field(ge=0.0)
    candidate_count: int = Field(ge=0)
    peak_memory_kb: float = Field(ge=0.0)
    match_count: int = Field(ge=0)
    operation_count: int = Field(ge=0)

    def deterministic_fingerprint(self) -> dict[str, int]:
        """Return the stable (timing/memory-free) portion for reproducibility."""
        return {
            "source_node_count": self.source_node_count,
            "target_node_count": self.target_node_count,
            "candidate_count": self.candidate_count,
            "match_count": self.match_count,
            "operation_count": self.operation_count,
        }
