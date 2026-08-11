"""Root-cause analyzer (REQ-073-080).

Distinguishes *root* operations (the structural edits that explain observed
differences) from *derived* effects. In the initial release derived effects
are downstream positional/path changes, which are represented as suppressed
effects in the suppression stage rather than as separate operations; the causal
graph therefore records the root operations and (when applicable) their links
to derived effects.

Ambiguity in the underlying match graph is surfaced as an ambiguous causal
graph so that no ambiguous relationship is silently converted into a
repairable conclusion (REQ-080, AC-038).
"""

from __future__ import annotations

from reconciliation.core.causality.objective import objective_score
from reconciliation.core.contracts.causality import (
    CandidateExplanation,
    CausalOperationGraph,
)
from reconciliation.core.contracts.evidence import Confidence
from reconciliation.core.contracts.matches import MatchGraph
from reconciliation.core.contracts.operations import StructuralOperationSet
from reconciliation.core.contracts.profiles import OperationType


class RootCauseAnalyzerService:
    """Default :class:`RootCauseAnalyzer` implementation."""

    def analyze(
        self, operations: StructuralOperationSet, graph: MatchGraph
    ) -> CausalOperationGraph:
        """Build a causal operation graph from classified operations.

        :param operations: The classified structural operations.
        :param graph: The match graph (used to detect ambiguity).
        :returns: A :class:`CausalOperationGraph` whose selected explanation
            lists the root operations. ``alternatives`` is populated only when
            the match graph is ambiguous, keeping ambiguity explicit.
        """
        roots = tuple(
            op.operation_id
            for op in operations.operations
            if op.type is not OperationType.MATCH
        )
        score = objective_score(operations.operations)
        # Explanation confidence is the mean operation confidence (a score, not
        # a calibrated probability), or full confidence when nothing changed.
        changed = [op for op in operations.operations if op.type is not OperationType.MATCH]
        confidence_value = (
            sum(op.confidence.value for op in changed) / len(changed) if changed else 1.0
        )
        selected = CandidateExplanation(
            explanation_id="explanation-primary",
            root_operation_ids=roots,
            links=(),
            objective_score=score,
            confidence=Confidence(value=round(confidence_value, 6)),
        )

        alternatives: tuple[CandidateExplanation, ...] = ()
        if graph.ambiguous:
            alternatives = (
                CandidateExplanation(
                    explanation_id="explanation-ambiguous-alternative",
                    root_operation_ids=roots,
                    links=(),
                    objective_score=score,
                    confidence=Confidence(value=round(confidence_value, 6)),
                ),
            )

        return CausalOperationGraph(selected=selected, alternatives=alternatives)
