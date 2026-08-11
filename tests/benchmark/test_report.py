"""Test the benchmark report generator (plan §8 'benchmark report is generated')."""

from __future__ import annotations

from reconciliation.benchmark.report import build_benchmark_report
from reconciliation.version import ENGINE_VERSION


def test_build_benchmark_report_structure() -> None:
    report = build_benchmark_report()
    assert report.engine_version == ENGINE_VERSION
    assert report.generated_at
    # Clean corpus is perfectly reconciled and deterministic.
    assert report.clean_quality.match_precision == 1.0
    assert report.clean_quality.deterministic_consistency is True
    assert report.ambiguous_quality.ambiguity_rate > 0.0
    assert len(report.performance) == 4


def test_render_markdown_contains_sections() -> None:
    markdown = build_benchmark_report().render_markdown()
    assert "# Reconciliation Benchmark Report" in markdown
    assert "## Quality (labeled corpus)" in markdown
    assert "## Performance (synthetic scenarios)" in markdown
    # No production threshold is declared validated.
    assert "No production thresholds are declared" in markdown
