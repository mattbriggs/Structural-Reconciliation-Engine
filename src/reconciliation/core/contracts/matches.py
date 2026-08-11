"""Match graph contracts (REQ-037-051, REQ-254-258).

The matcher emits a :class:`MatchGraph` rather than committing every node to a
single correspondence, preserving ambiguity and uncertainty (Objective 5).
The initial release supports one-to-one correspondence, but the contract is
shaped to permit future one-to-many/many-to-one states (REQ-040).
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field, model_validator

from reconciliation.core.contracts.base import StrictModel
from reconciliation.core.contracts.evidence import Confidence, Evidence, FeatureScore
from reconciliation.core.contracts.tree import NodeRef


class MatchState(str, Enum):
    """Correspondence states a candidate may hold (REQ-038)."""

    CONFIRMED = "CONFIRMED"
    CANDIDATE = "CANDIDATE"
    AMBIGUOUS = "AMBIGUOUS"
    REJECTED = "REJECTED"
    UNMATCHED = "UNMATCHED"


class ConstraintViolation(StrictModel):
    """A hard or soft constraint a candidate violates (REQ-041).

    :ivar constraint: Stable constraint identifier.
    :ivar hard: True for hard (disqualifying) constraints (REQ-042).
    :ivar message: Non-sensitive explanation.
    """

    constraint: str
    hard: bool
    message: str | None = None


class MatchCandidate(StrictModel):
    """A proposed correspondence between a source and target node.

    :ivar match_id: Stable identifier for this candidate.
    :ivar source_node_ref: Source-tree node reference.
    :ivar target_node_ref: Target-tree node reference.
    :ivar state: Correspondence state (REQ-038).
    :ivar score: Weighted feature score (REQ-046).
    :ivar confidence: Calibrated/uncalibrated match confidence (REQ-046).
    :ivar evidence: Supporting evidence; required for confirmed/ambiguous
        states (REQ-257).
    :ivar violated_soft_constraints: Soft constraints the candidate violates.
    :ivar hard_constraints: Hard constraints applicable to the candidate.
    :ivar alternative_match_ids: Competing candidates when ambiguous
        (REQ-256).
    :ivar profile_version: Matching profile version used (REQ-283).
    """

    match_id: str = Field(min_length=1)
    source_node_ref: NodeRef
    target_node_ref: NodeRef
    state: MatchState
    score: FeatureScore
    confidence: Confidence
    evidence: tuple[Evidence, ...] = ()
    violated_soft_constraints: tuple[ConstraintViolation, ...] = ()
    hard_constraints: tuple[ConstraintViolation, ...] = ()
    alternative_match_ids: tuple[str, ...] = ()
    profile_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def _evidence_required_for_asserted_states(self) -> MatchCandidate:
        """Confirmed/ambiguous matches require evidence (REQ-257) and alts (REQ-256)."""
        if self.state in (MatchState.CONFIRMED, MatchState.AMBIGUOUS) and not self.evidence:
            raise ValueError(
                f"{self.state.value} match {self.match_id!r} must include at least one evidence"
            )
        if self.state is MatchState.AMBIGUOUS and not self.alternative_match_ids:
            raise ValueError(
                f"ambiguous match {self.match_id!r} must reference at least one alternative"
            )
        if self.state is MatchState.CONFIRMED and any(c.hard for c in self.hard_constraints):
            raise ValueError(
                f"confirmed match {self.match_id!r} cannot violate a hard constraint (REQ-042)"
            )
        return self


class MatchGraph(StrictModel):
    """The complete set of correspondences produced by the matcher.

    :ivar candidates: All candidates in deterministic order.

    Invariant (REQ-255): no source or target node participates in more than
    one *confirmed* one-to-one match. Enforced here so downstream stages can
    rely on it.
    """

    candidates: tuple[MatchCandidate, ...] = ()

    @model_validator(mode="after")
    def _one_to_one_confirmed(self) -> MatchGraph:
        confirmed_sources: set[NodeRef] = set()
        confirmed_targets: set[NodeRef] = set()
        for c in self.candidates:
            if c.state is not MatchState.CONFIRMED:
                continue
            if c.source_node_ref in confirmed_sources:
                raise ValueError(
                    f"source node {c.source_node_ref!r} appears in multiple confirmed matches"
                )
            if c.target_node_ref in confirmed_targets:
                raise ValueError(
                    f"target node {c.target_node_ref!r} appears in multiple confirmed matches"
                )
            confirmed_sources.add(c.source_node_ref)
            confirmed_targets.add(c.target_node_ref)
        return self

    @property
    def confirmed(self) -> tuple[MatchCandidate, ...]:
        """Confirmed correspondences only."""
        return tuple(c for c in self.candidates if c.state is MatchState.CONFIRMED)

    @property
    def ambiguous(self) -> tuple[MatchCandidate, ...]:
        """Ambiguous correspondences only."""
        return tuple(c for c in self.candidates if c.state is MatchState.AMBIGUOUS)

    def confirmed_target_for(self, source_node_ref: NodeRef) -> NodeRef | None:
        """Return the confirmed target for a source node, if any."""
        for c in self.candidates:
            if c.state is MatchState.CONFIRMED and c.source_node_ref == source_node_ref:
                return c.target_node_ref
        return None

    def confirmed_source_for(self, target_node_ref: NodeRef) -> NodeRef | None:
        """Return the confirmed source for a target node, if any."""
        for c in self.candidates:
            if c.state is MatchState.CONFIRMED and c.target_node_ref == target_node_ref:
                return c.source_node_ref
        return None
