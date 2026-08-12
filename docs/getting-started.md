# Getting started

## Install

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Install optional extras only when working on those layers:

```bash
python -m pip install -e ".[xml]"          # XML/DITA adapters
python -m pip install -e ".[cli]"          # reconcile-localization console script
python -m pip install -e ".[api]"          # HTTP API
python -m pip install -e ".[reporting]"    # HTML report renderer
python -m pip install -e ".[persistence]"  # SQLite repositories
python -m pip install -e ".[all]"          # everything
```

!!! warning "Untrusted input"
    XML input is treated as untrusted. The parser disables external entity
    resolution and DTD loading and bounds size/depth/node count. See
    [Security](architecture/security.md).

## Compare two DITA maps (CLI)

```bash
reconcile-localization \
  --source source.ditamap \
  --locale fr-FR.ditamap \
  --locale-code fr-FR \
  --document-profile dita-map-v1 \
  --html report.html \
  --csv report.csv \
  --json result.json
```

The exit code separates technical failures from detected content findings — see
[CLI](api/cli.md).

## Compare generic JSON or YAML

Use the same command with a generic document profile:

```bash
reconcile-localization \
  --source source.json \
  --locale target.json \
  --locale-code und \
  --document-profile generic-json-v1 \
  --json result.json
```

```bash
reconcile-localization \
  --source source.yaml \
  --locale target.yaml \
  --locale-code und \
  --document-profile generic-yaml-v1 \
  --json result.json
```

The JSON/YAML adapters map documents into shared `data:*` canonical nodes.
Object/mapping order is ignored by profile; array/sequence order is preserved.

## Compare in Python (library)

The pure core consumes canonical trees and typed profiles directly. For a
worked example of building trees and reconciling them, see the
[Python API](api/python.md) reference and the `README`.

## Run the service

```bash
uvicorn --factory reconciliation.delivery.api.app:create_app --port 8000
```

Then `POST` a comparison to `/api/v1/localization-comparisons`. See the
[HTTP API](api/http.md) and [Deployment](operations/deployment.md).
