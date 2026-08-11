"""Synchronous job executor (REQ-007).

Runs each submitted job to completion in-process and records its terminal
state. This is the simplest executor and keeps behavior fully deterministic;
the threaded executor in :mod:`.in_memory` demonstrates the same port with
out-of-process-style asynchrony.
"""

from __future__ import annotations

import threading

from reconciliation.application.contracts.jobs import ComparisonRequest, JobRecord
from reconciliation.application.orchestration.comparison_job import ComparisonJobService


class SynchronousJobExecutor:
    """Executes comparison jobs synchronously on submit."""

    def __init__(self, service: ComparisonJobService) -> None:
        self._service = service
        self._records: dict[str, JobRecord] = {}
        self._lock = threading.Lock()

    def submit(self, request: ComparisonRequest) -> JobRecord:
        """Run the job immediately and store its terminal record."""
        outcome = self._service.run(request)
        with self._lock:
            self._records[outcome.record.job_id] = outcome.record
        return outcome.record

    def get(self, job_id: str) -> JobRecord | None:
        """Return the stored record for ``job_id``."""
        with self._lock:
            return self._records.get(job_id)
