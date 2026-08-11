"""Unit tests for individual pipeline-stage services and utilities."""

from __future__ import annotations

import pytest

from reconciliation.core.alignment.lcs import Op, align_sequences
from reconciliation.core.contracts.commands import (
    ExecutionContext,
    ReconcileTreesCommand,
    ResourceLimits,
)
from reconciliation.core.contracts.profiles import NormalizationProfile
from reconciliation.core.engine import DefaultReconciliationEngine
from reconciliation.core.errors import ResourceLimitExceededError
from reconciliation.core.metrics.calculator import tree_depth
from reconciliation.core.normalization.service import TreeNormalizerService
from tests.builders import (
    TreeBuilder,
    default_alignment_profile,
    default_matching_profile,
    default_normalization_profile,
    default_operation_profile,
    default_suppression_profile,
)


def test_align_sequences_lcs() -> None:
    script = align_sequences(["a", "b", "c"], ["a", "x", "c"])
    kinds = [op for op, _l, _r in script]
    assert kinds == [Op.ALIGN, Op.LEFT_ONLY, Op.RIGHT_ONLY, Op.ALIGN]


def test_align_sequences_empty() -> None:
    assert align_sequences([], []) == []
    assert [op for op, _l, _r in align_sequences(["a"], [])] == [Op.LEFT_ONLY]


def test_normalization_collapses_whitespace_and_excludes_metadata() -> None:
    tree = TreeBuilder("s", "r", node_type="map").child(
        "r", "a", content={"title": "  hello   world ", "audit": "x"}
    ).build()
    profile = NormalizationProfile(
        profile_id="n",
        version="v1",
        collapse_whitespace=True,
        nonsemantic_metadata_keys=frozenset({"audit"}),
    )
    result = TreeNormalizerService().normalize(tree, profile)
    node = result.tree.nodes["a"]
    assert node.content_properties["title"] == "hello world"
    assert "audit" not in node.content_properties
    # Each action is attributed to a rule (REQ-023).
    rules = {t.rule for t in result.trace}
    assert {"collapse-whitespace", "exclude-nonsemantic"} <= rules


def test_normalization_preserves_designated_keys() -> None:
    tree = TreeBuilder("s", "r", node_type="map").child(
        "r", "a", content={"code": "  A B  "}
    ).build()
    profile = NormalizationProfile(
        profile_id="n",
        version="v1",
        collapse_whitespace=True,
        preserve_property_keys=frozenset({"code"}),
    )
    result = TreeNormalizerService().normalize(tree, profile)
    assert result.tree.nodes["a"].content_properties["code"] == "  A B  "


def test_tree_depth() -> None:
    tree = (
        TreeBuilder("s", "r", node_type="map")
        .child("r", "a")
        .child("a", "b")
        .child("b", "c")
        .build()
    )
    assert tree_depth(tree) == 4


def _command(source, target, *, limits: ResourceLimits, incomplete: bool) -> ReconcileTreesCommand:
    return ReconcileTreesCommand(
        source_tree=source,
        target_tree=target,
        normalization_profile=default_normalization_profile(),
        matching_profile=default_matching_profile(),
        alignment_profile=default_alignment_profile(),
        operation_profile=default_operation_profile(),
        suppression_profile=default_suppression_profile(),
        execution_context=ExecutionContext(
            job_id="job", resource_limits=limits, incomplete_on_limit=incomplete
        ),
    )


def test_resource_limit_raises_by_default() -> None:
    # REQ-200: exceeding a limit produces a controlled failure.
    src = TreeBuilder("s", "r", node_type="map").child("r", "a").child("r", "b").build()
    tgt = TreeBuilder("t", "r", node_type="map").child("r", "a").build()
    command = _command(src, tgt, limits=ResourceLimits(max_node_count=2), incomplete=False)
    with pytest.raises(ResourceLimitExceededError) as exc:
        DefaultReconciliationEngine().reconcile(command)
    assert exc.value.code == "RESOURCE_LIMIT_EXCEEDED"


def test_resource_limit_incomplete_result() -> None:
    # REQ-173/200: opt-in explicitly-incomplete result instead of raising.
    src = TreeBuilder("s", "r", node_type="map").child("r", "a").child("r", "b").build()
    tgt = TreeBuilder("t", "r", node_type="map").child("r", "a").build()
    command = _command(src, tgt, limits=ResourceLimits(max_node_count=2), incomplete=True)
    result = DefaultReconciliationEngine().reconcile(command)
    assert result.complete is False
    assert any(d.code == "RESOURCE_LIMIT_EXCEEDED" for d in result.diagnostics)


def test_depth_limit_enforced() -> None:
    deep = (
        TreeBuilder("s", "r", node_type="map").child("r", "a").child("a", "b").build()
    )
    shallow = TreeBuilder("t", "r", node_type="map").child("r", "a").build()
    command = _command(deep, shallow, limits=ResourceLimits(max_tree_depth=2), incomplete=False)
    with pytest.raises(ResourceLimitExceededError):
        DefaultReconciliationEngine().reconcile(command)
