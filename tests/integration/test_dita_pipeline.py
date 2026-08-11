"""Integration tests: DITA XML -> canonical -> engine (REQ-033, AC-024, AC-036).

Exercises the full Phase-2 path with the packaged ``dita-map-v1`` profile
bundle: two DITA maps are adapted and reconciled. Locale-stable keys drive
identity so translated navtitles and a reorder do not break correspondence.
"""

from __future__ import annotations

from reconciliation.adapters.dita.map_adapter import DitaMapAdapter
from reconciliation.core.contracts.commands import ExecutionContext, ReconcileTreesCommand
from reconciliation.core.contracts.profiles import OperationType
from reconciliation.core.engine import DefaultReconciliationEngine
from reconciliation.profiles import load_named_bundle

SOURCE = """<map>
  <topicref keys="intro" href="intro.dita"><topicmeta><navtitle>Introduction</navtitle></topicmeta></topicref>
  <topicref keys="setup" href="setup.dita"><topicmeta><navtitle>Setup</navtitle></topicmeta></topicref>
  <topicref keys="publish" href="publish.dita"><topicmeta><navtitle>Publishing</navtitle></topicmeta></topicref>
</map>"""

# Locale: translated navtitles, publish/setup reordered.
LOCALE = """<map>
  <topicref keys="intro" href="intro.dita"><topicmeta><navtitle>Introducción</navtitle></topicmeta></topicref>
  <topicref keys="publish" href="publish.dita"><topicmeta><navtitle>Publicación</navtitle></topicmeta></topicref>
  <topicref keys="setup" href="setup.dita"><topicmeta><navtitle>Configuración</navtitle></topicmeta></topicref>
</map>"""


def _reconcile(source: str, locale: str):
    adapter = DitaMapAdapter()
    src = adapter.adapt_document(source, tree_id="src", document_uri="source.ditamap")
    loc = adapter.adapt_document(locale, tree_id="loc", document_uri="fr.ditamap")
    bundle = load_named_bundle("dita_map_v1")
    command = ReconcileTreesCommand(
        source_tree=src,
        target_tree=loc,
        normalization_profile=bundle.normalization,
        matching_profile=bundle.matching,
        alignment_profile=bundle.alignment,
        operation_profile=bundle.operation,
        suppression_profile=bundle.suppression,
        execution_context=ExecutionContext(job_id="dita-job"),
    )
    return DefaultReconciliationEngine().reconcile(command)


def test_translated_reordered_map_still_matches_by_keys() -> None:
    result = _reconcile(SOURCE, LOCALE)
    # AC-024: low lexical similarity of navtitles does not defeat key identity.
    assert len(result.match_graph.confirmed) == 4  # map + 3 topicrefs
    # AC-006: the swap is a single REORDER, not multiple moves.
    assert len(result.operations.of_type(OperationType.REORDER)) == 1
    assert not result.operations.of_type(OperationType.MOVE)


def test_translation_surfaces_as_update_not_delete_insert() -> None:
    result = _reconcile(SOURCE, LOCALE)
    # AC-008: content (navtitle) changed but identity preserved -> UPDATE.
    updates = result.operations.of_type(OperationType.UPDATE)
    assert len(updates) == 3
    assert not result.operations.of_type(OperationType.DELETE)
    assert not result.operations.of_type(OperationType.INSERT)


def test_result_records_exact_profile_versions() -> None:
    result = _reconcile(SOURCE, LOCALE)
    versions = result.profile_versions
    # AC-036: every result identifies the exact profile versions used.
    assert versions.matching_profile_version == "v1"
    assert versions.operation_profile_version == "v1"
    assert result.complete is True


def test_inserted_locale_topic_is_single_insert() -> None:
    locale_with_extra = """<map>
      <topicref keys="intro" href="intro.dita"/>
      <topicref keys="new" href="new.dita"/>
      <topicref keys="setup" href="setup.dita"/>
      <topicref keys="publish" href="publish.dita"/>
    </map>"""
    result = _reconcile(SOURCE, locale_with_extra)
    inserts = result.operations.of_type(OperationType.INSERT)
    assert len(inserts) == 1
