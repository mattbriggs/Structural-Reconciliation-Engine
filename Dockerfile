# Structural Reconciliation Engine — API service image.
#
# Runs as a non-root user, serves the FastAPI app, and requires no network
# access during XML adaptation (the parser disables external entities/DTDs).
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SRE_ARTIFACT_DIR=/var/lib/reconciliation/artifacts

# --- build/install layer ---------------------------------------------------
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip \
    && pip install ".[api,cli,reporting,persistence,xml,yaml]"

# --- runtime user & data dir ----------------------------------------------
RUN useradd --system --create-home --uid 10001 appuser \
    && mkdir -p "$SRE_ARTIFACT_DIR" \
    && chown -R appuser:appuser "$SRE_ARTIFACT_DIR"

USER appuser
EXPOSE 8000

# Liveness/readiness probes are served by the app (/health, /ready).
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

CMD ["uvicorn", "--factory", "reconciliation.delivery.api.app:create_app", \
     "--host", "0.0.0.0", "--port", "8000"]
