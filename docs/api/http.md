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

## Document profiles

The request `document_profile_id` selects the parser, canonical adapter, and
profile bundle:

| Profile id | Input shape |
|---|---|
| `dita-map-v1` | DITA map XML |
| `generic-xml-v1` | Vocabulary-agnostic XML |
| `generic-json-v1` | JSON data trees |
| `generic-yaml-v1` | YAML data trees |

JSON and YAML are mapped to shared `data:*` canonical node types. Object and
mapping children are unordered by profile; array and sequence children are
ordered.

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
