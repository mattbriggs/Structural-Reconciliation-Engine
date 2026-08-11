"""Threaded in-memory job executor (REQ-007).

Runs jobs on a background thread pool so ``submit`` returns immediately with a
non-terminal ``RUNNING`` record while the work proceeds asynchronously — all at
the application boundary, with the reconciliation kernel remaining synchronous.
``wait`` is provided for deterministic testing.
"""

from __future__ import annotations

import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor

from reconciliation.application.contracts.jobs import (
    ComparisonRequest,
    ComparisonState,
    JobRecord,
)
from reconciliation.application.orchestration.comparison_job import ComparisonJobService


class ThreadedJobExecutor:
    """Executes comparison jobs on a background thread pool.

    :param service: The comparison job service to run.
    :param max_workers: Thread pool size.
    """

    def __init__(self, service: ComparisonJobService, *, max_workers: int = 2) -> None:
        self._service = service
        self._pool = ThreadPoolExecutor(max_workers=max_workers)
        self._records: dict[str, JobRecord] = {}
        self._futures: dict[str, Future[None]] = {}
        self._lock = threading.Lock()

    def submit(self, request: ComparisonRequest) -> JobRecord:
        """Schedule the job and return a RUNNING record immediately."""
        job_id = request.job_id or f"job-{uuid.uuid4()}"
        request = request.model_copy(update={"job_id": job_id})
        running = JobRecord(
            job_id=job_id, state=ComparisonState.RUNNING, locale=request.locale
        )
        with self._lock:
            self._records[job_id] = running
            self._futures[job_id] = self._pool.submit(self._execute, request)
        return running

    def _execute(self, request: ComparisonRequest) -> None:
        outcome = self._service.run(request)
        with self._lock:
            self._records[outcome.record.job_id] = outcome.record

    def get(self, job_id: str) -> JobRecord | None:
        """Return the current record for ``job_id``."""
        with self._lock:
            return self._records.get(job_id)

    def wait(self, job_id: str, timeout: float | None = None) -> JobRecord | None:
        """Block until the job reaches a terminal state (testing helper)."""
        with self._lock:
            future = self._futures.get(job_id)
        if future is not None:
            future.result(timeout=timeout)
        return self.get(job_id)

    def shutdown(self) -> None:
        """Shut down the thread pool."""
        self._pool.shutdown(wait=True)
