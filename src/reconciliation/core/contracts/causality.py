"""Root-cause / causal operation graph contracts (REQ-073-080).

The analyzer distinguishes root operations from derived effects and can retain
multiple candidate explanations when none dominates the decision margin
(REQ-077). The graph must contain no invalid causal cycle.
"""

from __future__ import annotations

from pydantic import Field, model_validator

from reconciliation.core.contracts.base import StrictModel
from reconciliation.core.contracts.evidence import Confidence


class CausalLink(StrictModel):
    """A causal relationship asserting one operation explains another.

    :ivar root_operation_id: The explaining root operation.
    :ivar derived_operation_id: The operation explained as a derived effect.
    :ivar rationale: Non-sensitive explanation of why (REQ-079).
    """

    root_operation_id: str = Field(min_length=1)
    derived_operation_id: str = Field(min_length=1)
    rationale: str | None = None

    @model_validator(mode="after")
    def _no_self_link(self) -> CausalLink:
        if self.root_operation_id == self.derived_operation_id:
            raise ValueError("an operation cannot be its own causal root")
        return self


class CandidateExplanation(StrictModel):
    """One coherent explanation of the observed differences (REQ-074, REQ-077).

    :ivar explanation_id: Stable identifier.
    :ivar root_operation_ids: Operations designated as roots in this
        explanation.
    :ivar links: Causal links from roots to derived effects.
    :ivar objective_score: Explanatory objective score (higher is better).
    :ivar confidence: Confidence in this explanation.
    """

    explanation_id: str = Field(min_length=1)
    root_operation_ids: tuple[str, ...] = ()
    links: tuple[CausalLink, ...] = ()
    objective_score: float
    confidence: Confidence


class CausalOperationGraph(StrictModel):
    """The selected explanation plus retained alternatives.

    :ivar selected: The chosen explanation.
    :ivar alternatives: Retained competing explanations within the decision
        margin (REQ-077); empty when one explanation dominated.
    """

    selected: CandidateExplanation
    alternatives: tuple[CandidateExplanation, ...] = ()

    @model_validator(mode="after")
    def _acyclic(self) -> CausalOperationGraph:
        """Reject causal cycles among the selected explanation's links (REQ-073)."""
        adjacency: dict[str, list[str]] = {}
        for link in self.selected.links:
            adjacency.setdefault(link.root_operation_id, []).append(link.derived_operation_id)

        visiting: set[str] = set()
        visited: set[str] = set()

        def has_cycle(node: str) -> bool:
            visiting.add(node)
            for nxt in adjacency.get(node, ()):
                if nxt in visiting:
                    return True
                if nxt not in visited and has_cycle(nxt):
                    return True
            visiting.discard(node)
            visited.add(node)
            return False

        for start in list(adjacency):
            if start not in visited and has_cycle(start):
                raise ValueError("causal operation graph contains an invalid cycle")
        return self

    @property
    def is_ambiguous(self) -> bool:
        """True when competing explanations were retained (REQ-077)."""
        return bool(self.alternatives)
