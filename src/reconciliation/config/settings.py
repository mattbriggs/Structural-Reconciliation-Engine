"""Typed application settings (REQ-182, REQ-221, REQ-224, REQ-225).

Configuration is environment-driven via ``pydantic-settings`` with the ``SRE_``
prefix. Secrets are supplied only through the environment/injected secret
mechanisms — never hard-coded — and content redaction defaults to *on* so logs
do not leak source or translated text unless explicitly enabled.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Deployment settings.

    :ivar app_name: Logical application name for logs.
    :ivar log_level: Logging level (e.g. ``INFO``).
    :ivar log_json: Emit JSON logs (vs. console rendering).
    :ivar redact_content: Redact content values in logs/reports by default
        (REQ-221); disable only in a controlled environment.
    :ivar expose_filesystem_paths: Expose raw filesystem paths in responses
        (REQ-182); off by default.
    :ivar database_url: SQLAlchemy database URL.
    :ivar artifact_dir: Directory for generated report artifacts.
    :ivar retention_days: Optional retention period for inputs/results/reports
        and reviewer decisions (REQ-225); ``None`` means no automatic expiry.
    """

    model_config = SettingsConfigDict(env_prefix="SRE_", extra="ignore")

    app_name: str = "structural-reconciliation"
    log_level: str = "INFO"
    log_json: bool = True
    redact_content: bool = True
    expose_filesystem_paths: bool = False
    database_url: str = "sqlite+pysqlite:///:memory:"
    artifact_dir: str = "./artifacts"
    retention_days: int | None = None


@lru_cache
def get_settings() -> Settings:
    """Return cached process settings loaded from the environment."""
    return Settings()
