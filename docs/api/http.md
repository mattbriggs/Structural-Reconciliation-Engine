# HTTP API

Versioned under `/api/v1` (REQ-178). Build the app with the factory:

```bash
uvicorn --factory reconciliation.delivery.api.app:create_app --port 8000
```

## Endpoints

| Method | Path | Result |
|---|---|---|
| `POST` | `/api/v1/localization-comparisons` | Create/execute a comparison |
| `GET` | `/api/v1/localization-comparisons/{job_id}` | Lifecycle + summary |
| `GET` | `/api/v1/localization-comparisons/{job_id}/results` | JSON or CSV (content negotiation) |
| `GET` | `/api/v1/localization-comparisons/{job_id}/report` | HTML report |
| `POST` | `/api/v1/localization-comparisons/{job_id}/decisions` | Add a reviewer decision |
| `GET` | `/health`, `/ready` | Liveness / readiness |

## Errors (REQ-179, REQ-180)

Errors are structured:

```json
{ "code": "UNSUPPORTED_CONTRACT", "message": "...",
  "correlation_id": "corr-...", "retryable": false, "field": null }
```

Unsupported document profiles are rejected (`422 UNSUPPORTED_CONTRACT`,
REQ-181). Job responses omit filesystem artifact locations by default
(REQ-182).

## Content negotiation

`GET .../results` returns `application/json` by default, or `text/csv` when the
`Accept: text/csv` header is sent.
