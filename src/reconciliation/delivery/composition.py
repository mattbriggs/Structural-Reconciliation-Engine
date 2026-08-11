"""Composition root: build the default registry and comparison service.

This is the one place that imports concrete adapters and profiles and wires
them into the application services. Keeping it here preserves the application
layer's independence from concrete adapter implementations.
"""

from __future__ import annotations

from reconciliation.adapters.dita.map_adapter import DitaMapAdapter
from reconciliation.application.orchestration.comparison_job import ComparisonJobService
from reconciliation.application.orchestration.registry import DocumentProfileRegistry
from reconciliation.application.ports.artifacts import ArtifactStore
from reconciliation.application.ports.results import ComparisonResultRepository
from reconciliation.profiles import load_named_bundle

#: Default document profile id for the DITA map reference profile.
DEFAULT_PROFILE_ID = "dita-map-v1"


def build_default_registry() -> DocumentProfileRegistry:
    """Return a registry with the DITA map reference profile registered."""
    registry = DocumentProfileRegistry()
    registry.register(DEFAULT_PROFILE_ID, DitaMapAdapter(), load_named_bundle("dita_map_v1"))
    return registry


def build_comparison_service(
    *,
    registry: DocumentProfileRegistry | None = None,
    result_repository: ComparisonResultRepository | None = None,
    artifact_store: ArtifactStore | None = None,
) -> ComparisonJobService:
    """Build a comparison job service with default wiring."""
    return ComparisonJobService(
        registry or build_default_registry(),
        result_repository=result_repository,
        artifact_store=artifact_store,
    )
