"""Container packaging contract (plan §5 deployment notes).

Docker is not available in the unit-test environment, so this validates the
deployment *contract*: the ASGI app the container serves boots and answers
health/readiness probes, and the Dockerfile/compose enforce non-root execution
and secure defaults. The actual ``docker build`` is the release-time smoke test.
"""

from __future__ import annotations

import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

from fastapi.testclient import TestClient  # noqa: E402

from reconciliation.delivery.api.app import create_app  # noqa: E402

_ROOT = Path(__file__).resolve().parents[3]


def test_app_factory_boots_and_probes_respond() -> None:
    # This is exactly what `uvicorn --factory ...:create_app` serves.
    client = TestClient(create_app())
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200


def test_dockerfile_runs_non_root_with_healthcheck() -> None:
    dockerfile = (_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "USER appuser" in dockerfile  # non-root (REQ: run as non-root)
    assert "HEALTHCHECK" in dockerfile
    assert "--factory" in dockerfile and "reconciliation.delivery.api.app:create_app" in dockerfile


def test_compose_uses_secure_defaults() -> None:
    compose = (_ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert 'SRE_REDACT_CONTENT: "true"' in compose
    assert 'SRE_EXPOSE_FILESYSTEM_PATHS: "false"' in compose
    assert "no-new-privileges:true" in compose
