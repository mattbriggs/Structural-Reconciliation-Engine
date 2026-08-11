"""Tests for the filesystem artifact store (REQ-250, path safety)."""

from __future__ import annotations

import pytest

from reconciliation.application.ports.artifacts import ArtifactWriteError
from reconciliation.infrastructure.artifact_store import FilesystemArtifactStore


def test_write_and_read_roundtrip(tmp_path) -> None:
    store = FilesystemArtifactStore(tmp_path)
    ref = store.write("job-1", "report.html", "<html>café</html>", "text/html")
    assert ref.job_id == "job-1"
    assert ref.media_type == "text/html"
    assert ref.size_bytes > 0
    assert store.read(ref) == "<html>café</html>"


def test_empty_or_dotdot_component_is_rejected(tmp_path) -> None:
    store = FilesystemArtifactStore(tmp_path)
    # A component that sanitizes to nothing (pure traversal) is rejected.
    with pytest.raises(ArtifactWriteError):
        store.write("..", "passwd", "x", "text/plain")


def test_name_is_sanitized(tmp_path) -> None:
    store = FilesystemArtifactStore(tmp_path)
    ref = store.write("job-1", "../evil.csv", "data", "text/csv")
    # The traversal component is neutralized; the file stays under the base dir.
    assert str(tmp_path) in ref.location
    assert ".." not in ref.location.split("/")[-1]


def test_read_missing_artifact_raises(tmp_path) -> None:
    store = FilesystemArtifactStore(tmp_path)
    ref = store.write("job-1", "a.txt", "hi", "text/plain")
    missing = ref.model_copy(update={"location": str(tmp_path / "nope.txt")})
    with pytest.raises(ArtifactWriteError):
        store.read(missing)
