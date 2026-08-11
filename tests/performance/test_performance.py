"""Performance harness (REQ-196-201).

Exercises large, deep, repetitive, and high-edit-density trees, capturing
reproducible performance records (timing, candidate counts, peak memory).
Timing bounds are deliberately generous — these tests assert *reproducibility*
and *scaling shape*, not production latency targets (which remain open).
"""

from __future__ import annotations

import pytest

from reconciliation.benchmark.evaluator import measure_performance
from reconciliation.benchmark.generators import (
    deep_tree,
    high_edit_density_pair,
    repetitive_tree,
    wide_tree,
)

pytestmark = pytest.mark.performance


def test_wide_trees_scale_linearly_with_anchors() -> None:
    record = measure_performance("wide", wide_tree("s", 200), wide_tree("t", 200))
    assert record.match_count == 201  # root + 200 identified children
    # Stable identifiers act as anchors: candidate count stays ~linear (REQ-197).
    assert record.candidate_count <= 3 * record.source_node_count
    assert record.duration_ms < 30_000


def test_deep_trees_complete() -> None:
    record = measure_performance("deep", deep_tree("s", 80), deep_tree("t", 80))
    assert record.source_node_count == 80
    assert record.operation_count >= 1
    assert record.peak_memory_kb > 0


def test_repetitive_trees_are_handled() -> None:
    # Id-less repeated nodes have no anchors -> all-pairs similarity (quadratic).
    # Kept small so the test stays fast while documenting the characteristic.
    record = measure_performance("repetitive", repetitive_tree("s", 20), repetitive_tree("t", 20))
    assert record.candidate_count >= 20  # many candidate pairs generated
    assert record.duration_ms < 30_000


def test_high_edit_density_completes() -> None:
    source, target = high_edit_density_pair(120)
    record = measure_performance("high-edit", source, target)
    assert record.operation_count >= 1
    assert record.duration_ms < 30_000


def test_performance_record_is_reproducible() -> None:
    source, target = wide_tree("s", 100), wide_tree("t", 100)
    first = measure_performance("repro", source, target)
    second = measure_performance("repro", source, target)
    # Timing/memory vary, but counts are deterministic (REQ-202).
    assert first.deterministic_fingerprint() == second.deterministic_fingerprint()
