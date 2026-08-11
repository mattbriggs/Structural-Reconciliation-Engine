"""HTTP data-transfer objects for the API (REQ-178, REQ-179, REQ-182).

Response DTOs deliberately omit filesystem artifact locations so raw paths are
not exposed unless a deployment explicitly opts in (REQ-182).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from reconciliation.application.contracts.common import AuthoritativeSide
from reconciliation.application.contracts.jobs import ComparisonState
from reconciliation.application.contracts.reviews import DecisionType


class CreateComparisonRequest(BaseModel):
    """Request body to create and execute a comparison."""

    source_content: str
    locale_content: str
    locale: str = Field(min_length=1)
    document_profile_id: str = "dita-map-v1"
    authoritative_side: AuthoritativeSide = AuthoritativeSide.SOURCE


class JobResponse(BaseModel):
    """Job lifecycle and summary response (no artifact paths, REQ-182)."""

    job_id: str
    state: ComparisonState
    locale: str | None = None
    status_counts: dict[str, int] = {}
    direct_issue_count: int = 0
    correlation_id: str | None = None


class DecisionRequest(BaseModel):
    """Request body to record a reviewer decision."""

    issue_id: str = Field(min_length=1)
    decision: DecisionType
    reviewer_id: str | None = None
    reason: str | None = None
    comment: str | None = None
    overridden_status: str | None = None


class DecisionResponse(BaseModel):
    """A recorded reviewer decision."""

    decision_id: str
    job_id: str
    issue_id: str
    decision: DecisionType
    original_status: str
    overridden_status: str | None = None


class ErrorResponse(BaseModel):
    """RFC-style structured error (REQ-179, REQ-180)."""

    code: str
    message: str
    correlation_id: str | None = None
    retryable: bool = False
    field: str | None = None
