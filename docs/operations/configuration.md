# Configuration

Settings are environment-driven via `pydantic-settings` with the `SRE_` prefix.

| Setting | Env var | Default | Purpose |
|---|---|---|---|
| `redact_content` | `SRE_REDACT_CONTENT` | `true` | Redact content values in logs (REQ-221) |
| `expose_filesystem_paths` | `SRE_EXPOSE_FILESYSTEM_PATHS` | `false` | Expose raw paths in responses (REQ-182) |
| `log_level` | `SRE_LOG_LEVEL` | `INFO` | Logging level |
| `log_json` | `SRE_LOG_JSON` | `true` | JSON vs console logs |
| `database_url` | `SRE_DATABASE_URL` | in-memory SQLite | SQLAlchemy URL |
| `artifact_dir` | `SRE_ARTIFACT_DIR` | `./artifacts` | Artifact directory |
| `retention_days` | `SRE_RETENTION_DAYS` | none | Retention hook (REQ-225) |

Secrets are supplied only through the environment or an injected secret
mechanism — never hard-coded. Content redaction is **on** by default so logs do
not leak source or translated text.
