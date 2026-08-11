"""In-memory fakes implementing the application ports.

These let application-level tests run without a database or filesystem and
serve as the reference behavior that the SQLite/filesystem adapters must match
(see the shared repository contract tests).
"""

from __future__ import annotations

from reconciliation.application.contracts.localization import LocalizationValidationResult
from reconciliation.application.contracts.reviews import ReviewerDecision
from reconciliation.application.ports.artifacts import ArtifactReference, ArtifactWriteError
from reconciliation.application.ports.results import RepositoryError


class InMemoryComparisonResultRepository:
    """In-memory :class:`ComparisonResultRepository`."""

    def __init__(self) -> None:
        self._store: dict[str, LocalizationValidationResult] = {}

    def save(self, result: LocalizationValidationResult) -> None:
        self._store[result.job_id] = result

    def get(self, job_id: str) -> LocalizationValidationResult | None:
        return self._store.get(job_id)


class InMemoryReviewerDecisionRepository:
    """In-memory :class:`ReviewerDecisionRepository`."""

    def __init__(self) -> None:
        self._decisions: list[ReviewerDecision] = []

    def add(self, decision: ReviewerDecision) -> None:
        if any(d.decision_id == decision.decision_id for d in self._decisions):
            raise RepositoryError(f"duplicate decision {decision.decision_id!r}")
        self._decisions.append(decision)

    def list_for_job(self, job_id: str) -> tuple[ReviewerDecision, ...]:
        return tuple(d for d in self._decisions if d.job_id == job_id)


class InMemoryArtifactStore:
    """In-memory :class:`ArtifactStore`."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def write(self, job_id: str, name: str, content: str, media_type: str) -> ArtifactReference:
        key = f"{job_id}/{name}"
        self._store[key] = content
        return ArtifactReference(
            job_id=job_id,
            name=name,
            media_type=media_type,
            location=key,
            size_bytes=len(content.encode("utf-8")),
        )

    def read(self, reference: ArtifactReference) -> str:
        if reference.location not in self._store:
            raise ArtifactWriteError(f"missing artifact {reference.location!r}")
        return self._store[reference.location]
