"""Tests for the FastAPI service (REQ-178-182, content negotiation, decisions)."""

from __future__ import annotations

import json
import warnings

import pytest

warnings.filterwarnings("ignore")

from fastapi.testclient import TestClient  # noqa: E402

from reconciliation.delivery.api.app import create_app  # noqa: E402

SRC = (
    '<map><topicref keys="intro" href="i.dita"/>'
    '<topicref keys="setup" href="s.dita"/>'
    '<topicref keys="gone" href="g.dita"/></map>'
)
LOC = '<map><topicref keys="intro" href="i.dita"/><topicref keys="setup" href="s.dita"/></map>'
BASE = "/api/v1/localization-comparisons"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _create(client: TestClient) -> str:
    response = client.post(
        BASE, json={"source_content": SRC, "locale_content": LOC, "locale": "fr-FR"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["state"] == "COMPLETED"
    return body["job_id"]


def test_create_and_get_status(client: TestClient) -> None:
    job_id = _create(client)
    status = client.get(f"{BASE}/{job_id}")
    assert status.status_code == 200
    assert status.json()["job_id"] == job_id
    assert status.json()["status_counts"]


def test_results_content_negotiation(client: TestClient) -> None:
    job_id = _create(client)
    as_json = client.get(f"{BASE}/{job_id}/results", headers={"accept": "application/json"})
    assert as_json.status_code == 200
    assert as_json.headers["content-type"].startswith("application/json")
    assert json.loads(as_json.text)["job_id"] == job_id

    as_csv = client.get(f"{BASE}/{job_id}/results", headers={"accept": "text/csv"})
    assert as_csv.status_code == 200
    assert as_csv.headers["content-type"].startswith("text/csv")
    assert as_csv.text.startswith("job_id,")


def test_html_report(client: TestClient) -> None:
    job_id = _create(client)
    report = client.get(f"{BASE}/{job_id}/report", headers={"accept": "text/html"})
    assert report.status_code == 200
    assert report.headers["content-type"].startswith("text/html")
    assert "<main>" in report.text


def test_unknown_job_returns_structured_404(client: TestClient) -> None:
    response = client.get(f"{BASE}/nope")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_invalid_body_returns_structured_422(client: TestClient) -> None:
    response = client.post(BASE, json={"source_content": "x"})
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "INVALID_INPUT"


def test_unsupported_profile_is_rejected(client: TestClient) -> None:
    response = client.post(
        BASE,
        json={
            "source_content": SRC,
            "locale_content": LOC,
            "locale": "fr-FR",
            "document_profile_id": "no-such-profile",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "UNSUPPORTED_CONTRACT"


def test_reviewer_decision_endpoint_preserves_original(client: TestClient) -> None:
    job_id = _create(client)
    results = client.get(f"{BASE}/{job_id}/results", headers={"accept": "application/json"})
    issues = json.loads(results.text)["issues"]
    missing = next(i for i in issues if i["localization_status"] == "MISSING_IN_LOCALE")
    response = client.post(
        f"{BASE}/{job_id}/decisions",
        json={
            "issue_id": missing["issue_id"],
            "decision": "OVERRIDE",
            "overridden_status": "EXEMPT_LOCALE_VARIATION",
            "reviewer_id": "alice",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["original_status"] == "MISSING_IN_LOCALE"
    assert body["overridden_status"] == "EXEMPT_LOCALE_VARIATION"


def test_decision_on_unknown_issue_is_422(client: TestClient) -> None:
    job_id = _create(client)
    response = client.post(
        f"{BASE}/{job_id}/decisions", json={"issue_id": "nope", "decision": "ACCEPT"}
    )
    assert response.status_code == 422


def test_paths_not_exposed_in_status(client: TestClient) -> None:
    # REQ-182: the job response carries no filesystem artifact locations.
    job_id = _create(client)
    body = client.get(f"{BASE}/{job_id}").json()
    assert "artifacts" not in body
    assert "location" not in json.dumps(body)


def test_health_and_ready(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json() == {"status": "ready"}
