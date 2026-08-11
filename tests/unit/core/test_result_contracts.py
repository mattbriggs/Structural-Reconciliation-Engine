"""Unit tests for core result-contract invariants (REQ-254-267)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from reconciliation.core.contracts.causality import (
    CandidateExplanation,
    CausalLink,
    CausalOperationGraph,
)
from reconciliation.core.contracts.evidence import Confidence, Evidence, FeatureScore
from reconciliation.core.contracts.matches import MatchCandidate, MatchGraph, MatchState
from reconciliation.core.contracts.operations import StructuralOperation
from reconciliation.core.contracts.profiles import EvidenceType, OperationType
from reconciliation.core.contracts.suppression import IndependentDefectCheck, SuppressedEffect


def _confidence(v: float = 0.9) -> Confidence:
    return Confidence(value=v)


def _score(v: float = 0.9) -> FeatureScore:
    return FeatureScore(value=v)


def _evidence() -> Evidence:
    return Evidence(code=EvidenceType.PERSISTENT_ID, weight=0.5, value="id-1")


def _confirmed(match_id: str, source: str, target: str) -> MatchCandidate:
    return MatchCandidate(
        match_id=match_id,
        source_node_ref=source,
        target_node_ref=target,
        state=MatchState.CONFIRMED,
        score=_score(),
        confidence=_confidence(),
        evidence=(_evidence(),),
        profile_version="v1",
    )


def test_confirmed_match_requires_evidence() -> None:
    # REQ-257
    with pytest.raises(ValidationError):
        MatchCandidate(
            match_id="m",
            source_node_ref="s",
            target_node_ref="t",
            state=MatchState.CONFIRMED,
            score=_score(),
            confidence=_confidence(),
            evidence=(),
            profile_version="v1",
        )


def test_ambiguous_match_requires_alternatives() -> None:
    # REQ-256
    with pytest.raises(ValidationError):
        MatchCandidate(
            match_id="m",
            source_node_ref="s",
            target_node_ref="t",
            state=MatchState.AMBIGUOUS,
            score=_score(),
            confidence=_confidence(),
            evidence=(_evidence(),),
            alternative_match_ids=(),
            profile_version="v1",
        )


def test_confidence_out_of_range_rejected() -> None:
    # REQ-254
    with pytest.raises(ValidationError):
        Confidence(value=1.5)


def test_match_graph_enforces_one_to_one_confirmed() -> None:
    # REQ-255: no shared source node across confirmed matches.
    with pytest.raises(ValidationError):
        MatchGraph(
            candidates=(
                _confirmed("m1", "s1", "t1"),
                _confirmed("m2", "s1", "t2"),
            )
        )


def test_match_graph_accessors() -> None:
    graph = MatchGraph(candidates=(_confirmed("m1", "s1", "t1"),))
    assert graph.confirmed_target_for("s1") == "t1"
    assert graph.confirmed_source_for("t1") == "s1"
    assert graph.confirmed_target_for("nope") is None


def test_reorder_requires_two_siblings() -> None:
    # REQ-262
    with pytest.raises(ValidationError):
        StructuralOperation(
            operation_id="op",
            type=OperationType.REORDER,
            source_node_refs=("only-one",),
            confidence=_confidence(),
            match_ids=("m1",),
        )


def test_move_requires_changed_parent_and_match() -> None:
    # REQ-263 / REQ-066
    with pytest.raises(ValidationError):
        StructuralOperation(
            operation_id="op",
            type=OperationType.MOVE,
            from_parent_ref="p",
            to_parent_ref="p",  # unchanged parent
            confidence=_confidence(),
            match_ids=("m1",),
        )


def test_suppressed_effect_rejects_retained_defect() -> None:
    # REQ-084 / REQ-266
    with pytest.raises(ValidationError):
        SuppressedEffect(
            effect_id="e",
            root_operation_id="op",
            suppression_rule_id="r",
            category="X",
            confidence=_confidence(),
            independent_defect_check=IndependentDefectCheck.DEFECT_RETAINED,
        )


def test_causal_graph_rejects_cycle() -> None:
    explanation = CandidateExplanation(
        explanation_id="x",
        root_operation_ids=("a",),
        links=(
            CausalLink(root_operation_id="a", derived_operation_id="b"),
            CausalLink(root_operation_id="b", derived_operation_id="a"),
        ),
        objective_score=1.0,
        confidence=_confidence(),
    )
    with pytest.raises(ValidationError):
        CausalOperationGraph(selected=explanation)
