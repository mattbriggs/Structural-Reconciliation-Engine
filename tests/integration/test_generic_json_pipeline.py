"""Integration tests for generic JSON document reconciliation."""

from __future__ import annotations

from reconciliation.adapters.json.canonical_adapter import JsonDocumentAdapter
from reconciliation.core.contracts.commands import ExecutionContext, ReconcileTreesCommand
from reconciliation.core.contracts.profiles import OperationType
from reconciliation.core.engine import DefaultReconciliationEngine
from reconciliation.profiles import load_named_bundle


def _reconcile(source: str, target: str):
    adapter = JsonDocumentAdapter()
    src = adapter.adapt_document(source, tree_id="src", document_uri="source.json")
    tgt = adapter.adapt_document(target, tree_id="tgt", document_uri="target.json")
    bundle = load_named_bundle("generic_json_v1")
    command = ReconcileTreesCommand(
        source_tree=src,
        target_tree=tgt,
        normalization_profile=bundle.normalization,
        matching_profile=bundle.matching,
        alignment_profile=bundle.alignment,
        operation_profile=bundle.operation,
        suppression_profile=bundle.suppression,
        execution_context=ExecutionContext(job_id="json-job"),
    )
    return DefaultReconciliationEngine().reconcile(command)


def test_json_object_field_reorder_is_not_structural_reorder() -> None:
    result = _reconcile('{"a": 1, "b": 2}', '{"b": 2, "a": 1}')

    assert not result.operations.of_type(OperationType.REORDER)
    assert not result.operations.of_type(OperationType.INSERT)
    assert not result.operations.of_type(OperationType.DELETE)


def test_json_array_reorder_is_reported_as_reorder() -> None:
    result = _reconcile(
        '{"items": ["a", "b", "c"]}',
        '{"items": ["a", "c", "b"]}',
    )

    assert len(result.operations.of_type(OperationType.REORDER)) == 1
    assert not result.operations.of_type(OperationType.INSERT)
    assert not result.operations.of_type(OperationType.DELETE)


def test_json_scalar_field_update_is_update_not_delete_insert() -> None:
    result = _reconcile('{"name": "Ada"}', '{"name": "Grace"}')

    assert result.operations.of_type(OperationType.UPDATE)
    assert not result.operations.of_type(OperationType.INSERT)
    assert not result.operations.of_type(OperationType.DELETE)


def test_json_field_addition_is_single_insert() -> None:
    result = _reconcile('{"name": "Ada"}', '{"name": "Ada", "active": true}')

    inserts = result.operations.of_type(OperationType.INSERT)
    assert len(inserts) == 1
    assert inserts[0].target_node_refs == ("n.0.1",)
