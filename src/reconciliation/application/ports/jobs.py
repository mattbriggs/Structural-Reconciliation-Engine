"""Job executor port (REQ-007).

Abstracts *how* a comparison job runs — synchronously in-process, in a
background thread, or on a queue — so asynchronous execution lives entirely at
the application boundary and never inside the reconciliation kernel.
"""

from __future__ import annotations

from typing import Protocol

from reconciliation.application.contracts.jobs import ComparisonRequest, JobRecord


class JobExecutorPort(Protocol):
    """Submits comparison jobs and reports their lifecycle state."""

    def submit(self, request: ComparisonRequest) -> JobRecord:
        """Submit a job; returns its initial (possibly non-terminal) record."""
        ...

    def get(self, job_id: str) -> JobRecord | None:
        """Return the current record for ``job_id``, or ``None`` if unknown."""
        ...
