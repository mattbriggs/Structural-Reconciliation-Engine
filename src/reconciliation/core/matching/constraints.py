"""Hard and soft match constraints (Specification pattern, REQ-042).

A *hard* constraint disqualifies a candidate outright (it can never reach the
confirmed state); a *soft* constraint is recorded but does not disqualify. The
node-type constraint is the canonical hard constraint (REQ-028): identifiers
must not override an incompatible type (REQ-036, AC-011).
"""

from __future__ import annotations

from reconciliation.core.contracts.matches import ConstraintViolation
from reconciliation.core.contracts.profiles import MatchingProfile
from reconciliation.core.evidence.extractor import NodeEvidence


def evaluate_constraints(
    source: NodeEvidence,
    target: NodeEvidence,
    profile: MatchingProfile,
) -> tuple[tuple[ConstraintViolation, ...], tuple[ConstraintViolation, ...]]:
    """Evaluate hard and soft constraints for a candidate pair.

    :param source: Source node evidence.
    :param target: Target node evidence.
    :param profile: Active matching profile.
    :returns: A ``(hard, soft)`` pair of violation tuples. A non-empty ``hard``
        tuple means the candidate must not be confirmed.
    """
    hard: list[ConstraintViolation] = []
    soft: list[ConstraintViolation] = []

    if source.node_type != target.node_type:
        violation = ConstraintViolation(
            constraint="NODE_TYPE_COMPATIBILITY",
            hard=profile.hard_constraint_node_type,
            message=f"node types differ: {source.node_type!r} vs {target.node_type!r}",
        )
        (hard if profile.hard_constraint_node_type else soft).append(violation)

    return tuple(hard), tuple(soft)
