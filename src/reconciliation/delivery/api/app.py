"""FastAPI application factory (REQ-178).

Assembles routers, structured error handlers, and application state. Health and
readiness endpoints support container deployment (plan §5 deployment note).
"""

from __future__ import annotations

from fastapi import FastAPI

from reconciliation.delivery.api.dependencies import ApiState, build_default_state
from reconciliation.delivery.api.error_handlers import register_error_handlers
from reconciliation.delivery.api.routers import comparisons, decisions
from reconciliation.version import __version__


def create_app(state: ApiState | None = None) -> FastAPI:
    """Create the FastAPI application.

    :param state: Optional pre-built application state (for tests/deployments);
        a default in-memory-SQLite state is built when omitted.
    :returns: A configured :class:`FastAPI` application.
    """
    app = FastAPI(
        title="Structural Reconciliation Engine",
        version=__version__,
        description="Source-to-locale XML reconciliation service.",
    )
    app.state.api = state or build_default_state()
    register_error_handlers(app)
    app.include_router(comparisons.router)
    app.include_router(decisions.router)

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        """Liveness probe."""
        return {"status": "ok"}

    @app.get("/ready", tags=["ops"])
    def ready() -> dict[str, str]:
        """Readiness probe."""
        return {"status": "ready"}

    return app
