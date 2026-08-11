"""Artifact store port and reference contract (REQ-250, SRS §8.8).

Report artifacts (HTML/CSV/JSON) are written through this port so storage is
replaceable. A renderer or artifact failure must never delete the underlying
result (the result lives in its own repository); a failed write raises
:class:`ArtifactWriteError`.
"""

from __future__ import annotations

from typing import Protocol

from reconciliation.core.contracts.base import StrictModel


class ArtifactWriteError(Exception):
    """Writing a report artifact failed."""

    code = "ARTIFACT_WRITE_FAILED"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ArtifactReference(StrictModel):
    """A reference to a stored report artifact.

    :ivar job_id: The comparison job.
    :ivar name: Logical artifact name (e.g. ``report.html``).
    :ivar media_type: The artifact's media type.
    :ivar location: An opaque locator (path or URI); may be redacted in
        responses per deployment policy (REQ-182).
    :ivar size_bytes: Size of the written artifact.
    """

    job_id: str
    name: str
    media_type: str
    location: str
    size_bytes: int


class ArtifactStore(Protocol):
    """Writes and reads report artifacts."""

    def write(self, job_id: str, name: str, content: str, media_type: str) -> ArtifactReference:
        """Write an artifact and return its reference.

        :raises ArtifactWriteError: If the artifact cannot be written.
        """
        ...

    def read(self, reference: ArtifactReference) -> str:
        """Read back a previously written artifact's content."""
        ...
