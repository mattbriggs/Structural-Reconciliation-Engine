"""Contract tests for the result and decision repositories.

Each behavioral test runs against both the in-memory fake and the SQLite
adapter, so the persistent implementation is held to the same contract
(REQ-211, REQ-213).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from reconciliation.application.contracts.reviews import (
    DecisionType,
    ReviewerDecision,
)
from reconciliation.application.ports.results import RepositoryError
from reconciliation.infrastructure.persistence.database import Database
from reconciliation.infrastructure.persistence.decision_repository import (
    SqliteReviewerDecisionRepository,
)
from reconciliation.infrastructure.persistence.result_repository import (
    SqliteComparisonResultRepository,
)
from tests.app_builders import localize
from tests.builders import TreeBuilder
from tests.fakes import (
    InMemoryComparisonResultRepository,
    InMemoryReviewerDecisionRepository,
)


@pytest.fixture
def db() -> Database:
    database = Database()
    database.create_all()
    yield database
    database.dispose()


def _result(job_id: str = "job-1"):
    src = TreeBuilder("s", "r", node_type="map")
    src.child("r", "a", identity={"id": "a"}).child("r", "b", identity={"id": "b"})
    tgt = TreeBuilder("t", "r", node_type="map")
    tgt.child("r", "a", identity={"id": "a"})
    return localize(src.build(), tgt.build(), job_id=job_id)


def _decision(decision_id: str, job_id: str = "job-1") -> ReviewerDecision:
    return ReviewerDecision(
        decision_id=decision_id,
        job_id=job_id,
        issue_id="issue-1",
        decision=DecisionType.ACCEPT,
        original_status="MISSING_IN_LOCALE",
        decided_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _result_repos(db: Database):
    return [InMemoryComparisonResultRepository(), SqliteComparisonResultRepository(db.session_factory)]


def _decision_repos(db: Database):
    return [InMemoryReviewerDecisionRepository(), SqliteReviewerDecisionRepository(db.session_factory)]


def test_result_repository_roundtrip(db: Database) -> None:
    result = _result()
    for repo in _result_repos(db):
        assert repo.get("job-1") is None
        repo.save(result)
        loaded = repo.get("job-1")
        assert loaded is not None
        assert loaded.job_id == "job-1"
        assert loaded == result  # exact contract round-trip


def test_result_repository_upsert(db: Database) -> None:
    result = _result()
    for repo in _result_repos(db):
        repo.save(result)
        repo.save(result)  # second save must not raise or duplicate
        assert repo.get("job-1") is not None


def test_decision_repository_append_and_list(db: Database) -> None:
    for repo in _decision_repos(db):
        repo.add(_decision("d1"))
        repo.add(_decision("d2"))
        listed = repo.list_for_job("job-1")
        assert [d.decision_id for d in listed] == ["d1", "d2"]
        assert repo.list_for_job("other") == ()


def test_decision_repository_rejects_duplicate(db: Database) -> None:
    for repo in _decision_repos(db):
        repo.add(_decision("dup"))
        with pytest.raises(RepositoryError):
            repo.add(_decision("dup"))


def test_implementations_satisfy_port_protocols(db: Database) -> None:
    # Both the fakes and the SQLite adapters structurally satisfy the ports.
    from reconciliation.application.ports.decisions import ReviewerDecisionRepository
    from reconciliation.application.ports.results import ComparisonResultRepository

    result_repo: ComparisonResultRepository = SqliteComparisonResultRepository(db.session_factory)
    decision_repo: ReviewerDecisionRepository = SqliteReviewerDecisionRepository(db.session_factory)
    assert hasattr(result_repo, "save") and hasattr(result_repo, "get")
    assert hasattr(decision_repo, "add") and hasattr(decision_repo, "list_for_job")
    assert hasattr(InMemoryComparisonResultRepository(), "get")
    assert hasattr(InMemoryReviewerDecisionRepository(), "list_for_job")


def test_result_persists_to_disk(tmp_path) -> None:
    # A file-backed SQLite database persists across repository instances.
    url = f"sqlite+pysqlite:///{tmp_path / 'results.db'}"
    db1 = Database(url)
    db1.create_all()
    SqliteComparisonResultRepository(db1.session_factory).save(_result("job-disk"))
    db1.dispose()

    db2 = Database(url)
    loaded = SqliteComparisonResultRepository(db2.session_factory).get("job-disk")
    db2.dispose()
    assert loaded is not None
    assert loaded.job_id == "job-disk"
