"""Composition root: build the default registry and comparison service.

This is the one place that imports concrete adapters and profiles and wires
them into the application services. Keeping it here preserves the application
layer's independence from concrete adapter implementations.
"""

from __future__ import annotations

from reconciliation.adapters.dita.map_adapter import DitaMapAdapter
from reconciliation.adapters.json.canonical_adapter import JsonDocumentAdapter
from reconciliation.adapters.xml.canonical_adapter import GenericXmlDocumentAdapter
from reconciliation.adapters.yaml.canonical_adapter import YamlDocumentAdapter
from reconciliation.application.orchestration.comparison_job import ComparisonJobService
from reconciliation.application.orchestration.registry import DocumentProfileRegistry
from reconciliation.application.ports.artifacts import ArtifactStore
from reconciliation.application.ports.results import ComparisonResultRepository
from reconciliation.profiles import load_named_bundle

#: Default document profile id for the DITA map reference profile.
DEFAULT_PROFILE_ID = "dita-map-v1"
GENERIC_XML_PROFILE_ID = "generic-xml-v1"
GENERIC_JSON_PROFILE_ID = "generic-json-v1"
GENERIC_YAML_PROFILE_ID = "generic-yaml-v1"


def build_default_registry() -> DocumentProfileRegistry:
    """Return a registry with the built-in document profiles registered."""
    registry = DocumentProfileRegistry()
    registry.register(
        GENERIC_XML_PROFILE_ID,
        GenericXmlDocumentAdapter(),
        load_named_bundle("generic_xml_v1"),
    )
    registry.register(
        GENERIC_JSON_PROFILE_ID,
        JsonDocumentAdapter(),
        load_named_bundle("generic_json_v1"),
    )
    registry.register(
        GENERIC_YAML_PROFILE_ID,
        YamlDocumentAdapter(),
        load_named_bundle("generic_yaml_v1"),
    )
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
