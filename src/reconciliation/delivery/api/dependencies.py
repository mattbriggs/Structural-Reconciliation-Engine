"""API application state and dependency wiring (composition root).

Holds the comparison service, repositories, and reviewer-decision service used
by the routers. A default state uses an in-memory SQLite database; production
deployments inject their own repositories and artifact store.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from reconciliation.application.contracts.jobs import JobRecord
from reconciliation.application.orchestration.comparison_job import ComparisonJobService
from reconciliation.application.services.reviewer_decisions import ReviewerDecisionService
from reconciliation.delivery.composition import build_comparison_service
from reconciliation.infrastructure.persistence.database import Database
from reconciliation.infrastructure.persistence.decision_repository import (
    SqliteReviewerDecisionRepository,
)
from reconciliation.infrastructure.persistence.result_repository import (
    SqliteComparisonResultRepository,
)


@dataclass
class ApiState:
    """Mutable application state shared by API routers."""

    service: ComparisonJobService
    result_repository: SqliteComparisonResultRepository
    decision_repository: SqliteReviewerDecisionRepository
    decision_service: ReviewerDecisionService
    jobs: dict[str, JobRecord] = field(default_factory=dict)


def build_default_state() -> ApiState:
    """Build API state backed by an in-memory SQLite database."""
    database = Database()
    database.create_all()
    result_repo = SqliteComparisonResultRepository(database.session_factory)
    decision_repo = SqliteReviewerDecisionRepository(database.session_factory)
    service = build_comparison_service(result_repository=result_repo)
    return ApiState(
        service=service,
        result_repository=result_repo,
        decision_repository=decision_repo,
        decision_service=ReviewerDecisionService(),
    )
