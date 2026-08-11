"""Explanatory objective for root-cause analysis (REQ-074, REQ-075).

The objective deliberately does **not** minimize operation count alone
(REQ-074). It balances edit cost against confidence-weighted plausibility so a
single high-confidence MOVE is preferred over many low-confidence edits that
happen to be more numerous. Costs and weights are profile-tunable inputs
(REQ-076); defaults here are illustrative, not calibrated production values.
"""

from __future__ import annotations

from reconciliation.core.contracts.operations import StructuralOperation
from reconciliation.core.contracts.profiles import OperationType

#: Illustrative per-operation edit costs. Not a calibrated production profile.
DEFAULT_OPERATION_COST: dict[OperationType, float] = {
    OperationType.MATCH: 0.0,
    OperationType.UPDATE: 1.0,
    OperationType.INSERT: 1.0,
    OperationType.DELETE: 1.0,
    OperationType.MOVE: 1.5,
    OperationType.REORDER: 1.2,
}


def objective_score(operations: tuple[StructuralOperation, ...]) -> float:
    """Score an explanation: higher is a better (more plausible, cheaper) fit.

    The score rewards confidence and penalizes edit cost::

        score = sum(confidence) - sum(edit_cost)

    :param operations: The operations forming the explanation.
    :returns: A real-valued objective score.
    """
    plausibility = sum(op.confidence.value for op in operations)
    cost = sum(DEFAULT_OPERATION_COST.get(op.type, 1.0) for op in operations)
    return round(plausibility - cost, 6)
