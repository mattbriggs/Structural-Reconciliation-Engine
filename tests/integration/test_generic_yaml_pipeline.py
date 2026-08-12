"""Integration tests for generic YAML document reconciliation."""

from __future__ import annotations

from reconciliation.adapters.json.canonical_adapter import JsonDocumentAdapter
from reconciliation.adapters.yaml.canonical_adapter import YamlDocumentAdapter
from reconciliation.core.contracts.commands import ExecutionContext, ReconcileTreesCommand
from reconciliation.core.contracts.profiles import OperationType
from reconciliation.core.engine import DefaultReconciliationEngine
from reconciliation.profiles import load_named_bundle


def _reconcile(source: str, target: str):
    adapter = YamlDocumentAdapter()
    src = adapter.adapt_document(source, tree_id="src", document_uri="source.yaml")
    tgt = adapter.adapt_document(target, tree_id="tgt", document_uri="target.yaml")
    bundle = load_named_bundle("generic_yaml_v1")
    command = ReconcileTreesCommand(
        source_tree=src,
        target_tree=tgt,
        normalization_profile=bundle.normalization,
        matching_profile=bundle.matching,
        alignment_profile=bundle.alignment,
        operation_profile=bundle.operation,
        suppression_profile=bundle.suppression,
        execution_context=ExecutionContext(job_id="yaml-job"),
    )
    return DefaultReconciliationEngine().reconcile(command)


def test_yaml_mapping_reorder_is_not_structural_reorder() -> None:
    result = _reconcile("a: 1\nb: 2\n", "b: 2\na: 1\n")

    assert not result.operations.of_type(OperationType.REORDER)
    assert not result.operations.of_type(OperationType.INSERT)
    assert not result.operations.of_type(OperationType.DELETE)


def test_yaml_sequence_reorder_is_reported_as_reorder() -> None:
    result = _reconcile(
        "items:\n  - a\n  - b\n  - c\n",
        "items:\n  - a\n  - c\n  - b\n",
    )

    assert len(result.operations.of_type(OperationType.REORDER)) == 1
    assert not result.operations.of_type(OperationType.INSERT)
    assert not result.operations.of_type(OperationType.DELETE)


def test_equivalent_json_and_yaml_use_compatible_data_node_types() -> None:
    json_tree = JsonDocumentAdapter().adapt_document(
        '{"name": "Ada", "roles": ["admin"]}',
        tree_id="json",
    )
    yaml_tree = YamlDocumentAdapter().adapt_document(
        "name: Ada\nroles:\n  - admin\n",
        tree_id="yaml",
    )

    assert [node.node_type for node in json_tree.nodes.values()] == [
        node.node_type for node in yaml_tree.nodes.values()
    ]
