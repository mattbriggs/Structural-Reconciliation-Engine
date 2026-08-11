"""Tests for typed settings (REQ-182, REQ-221, REQ-225)."""

from __future__ import annotations

from reconciliation.config.settings import Settings


def test_secure_defaults() -> None:
    settings = Settings()
    # Content redaction on and path exposure off by default.
    assert settings.redact_content is True
    assert settings.expose_filesystem_paths is False
    assert settings.retention_days is None


def test_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("SRE_REDACT_CONTENT", "false")
    monkeypatch.setenv("SRE_EXPOSE_FILESYSTEM_PATHS", "true")
    monkeypatch.setenv("SRE_RETENTION_DAYS", "30")
    settings = Settings()
    assert settings.redact_content is False
    assert settings.expose_filesystem_paths is True
    assert settings.retention_days == 30
