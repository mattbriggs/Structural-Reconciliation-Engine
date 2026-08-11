# Deployment

A container image and `compose.yaml` are provided for the optional API
deployment.

```bash
docker build -t structural-reconciliation:local .
docker compose up
```

## Container properties

- Runs as a **non-root** user (`appuser`, uid 10001).
- Requires **no network access** during XML adaptation (the parser disables
  external entities/DTDs).
- Serves `/health` and `/ready` probes; the image declares a `HEALTHCHECK`.
- Accepts configuration and secrets only through the environment.
- A mounted volume holds the SQLite database and report artifacts.

SQLite is suitable for local/single-node deployments; production database
selection remains an infrastructure decision — point `SRE_DATABASE_URL` at your
database and inject the appropriate repositories.
