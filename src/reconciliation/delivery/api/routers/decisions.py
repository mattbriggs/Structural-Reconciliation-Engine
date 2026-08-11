"""Reviewer decision endpoint (REQ-128-133, AC-030)."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from reconciliation.application.contracts.reviews import ReviewerDecisionCommand
from reconciliation.application.errors import ComparisonRejectedError
from reconciliation.delivery.api.dependencies import ApiState
from reconciliation.delivery.api.dtos import DecisionRequest, DecisionResponse
from reconciliation.delivery.api.error_handlers import error_response

router = APIRouter(prefix="/api/v1/localization-comparisons", tags=["decisions"])


def _state(request: Request) -> ApiState:
    return request.app.state.api  # type: ignore[no-any-return]


@router.post("/{job_id}/decisions", status_code=201)
def add_decision(job_id: str, body: DecisionRequest, request: Request) -> Response:
    """Record an additive reviewer decision against a stored result."""
    state = _state(request)
    result = state.result_repository.get(job_id)
    if result is None:
        return error_response(404, "NOT_FOUND", f"no result for job {job_id!r}")
    command = ReviewerDecisionCommand(
        job_id=job_id,
        issue_id=body.issue_id,
        decision=body.decision,
        reviewer_id=body.reviewer_id,
        reason=body.reason,
        comment=body.comment,
        overridden_status=body.overridden_status,
    )
    try:
        decision = state.decision_service.record(command, result)
    except ComparisonRejectedError as exc:
        return error_response(422, exc.code, exc.message)
    state.decision_repository.add(decision)
    response = DecisionResponse(
        decision_id=decision.decision_id,
        job_id=decision.job_id,
        issue_id=decision.issue_id,
        decision=decision.decision,
        original_status=decision.original_status,
        overridden_status=decision.overridden_status,
    )
    return Response(
        response.model_dump_json(), media_type="application/json", status_code=201
    )
