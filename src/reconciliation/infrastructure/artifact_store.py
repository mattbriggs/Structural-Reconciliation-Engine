"""Filesystem artifact store (REQ-250, SRS §8.8).

Writes report artifacts under a per-job directory and returns a reference. A
write failure raises :class:`ArtifactWriteError`; because results live in a
separate repository, a failed or partial artifact write never removes the
underlying result. Job/name components are sanitized to prevent path traversal.
"""

from __future__ import annotations

import re
from pathlib import Path

from reconciliation.application.ports.artifacts import (
    ArtifactReference,
    ArtifactStore,
    ArtifactWriteError,
)

_SAFE = re.compile(r"[^A-Za-z0-9._-]")


def _sanitize(component: str) -> str:
    cleaned = _SAFE.sub("_", component).strip("._")
    if not cleaned or cleaned in {".", ".."}:
        raise ArtifactWriteError(f"unsafe artifact path component: {component!r}")
    return cleaned


class FilesystemArtifactStore(ArtifactStore):
    """Stores artifacts as files under a base directory.

    :param base_dir: Root directory for artifacts (created on demand).
    """

    def __init__(self, base_dir: str | Path) -> None:
        self._base = Path(base_dir)

    def write(self, job_id: str, name: str, content: str, media_type: str) -> ArtifactReference:
        """Write an artifact and return its reference."""
        try:
            job_dir = self._base / _sanitize(job_id)
            job_dir.mkdir(parents=True, exist_ok=True)
            path = job_dir / _sanitize(name)
            data = content.encode("utf-8")
            path.write_bytes(data)
            return ArtifactReference(
                job_id=job_id,
                name=name,
                media_type=media_type,
                location=str(path),
                size_bytes=len(data),
            )
        except ArtifactWriteError:
            raise
        except OSError as exc:
            raise ArtifactWriteError(f"failed to write artifact {name!r}: {exc}") from exc

    def read(self, reference: ArtifactReference) -> str:
        """Read back a previously written artifact's content."""
        try:
            return Path(reference.location).read_text(encoding="utf-8")
        except OSError as exc:
            raise ArtifactWriteError(f"failed to read artifact {reference.name!r}: {exc}") from exc
