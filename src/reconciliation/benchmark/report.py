"""Benchmark report generation (plan §7, §8 "benchmark report is generated").

Assembles quality metrics over the labeled corpus and performance records for
the synthetic scenarios into a single report, renderable as Markdown. Reports
measured facts only — no production thresholds are declared "validated".
"""

from __future__ import annotations

from datetime import UTC, datetime

from reconciliation.benchmark.contracts import PerformanceRecord, QualityMetrics
from reconciliation.benchmark.corpus import ambiguous_cases, clean_cases
from reconciliation.benchmark.evaluator import evaluate_quality, measure_performance
from reconciliation.benchmark.generators import (
    deep_tree,
    high_edit_density_pair,
    repetitive_tree,
    wide_tree,
)
from reconciliation.core.contracts.base import StrictModel
from reconciliation.version import ENGINE_VERSION


class BenchmarkReport(StrictModel):
    """A generated benchmark report (quality + performance)."""

    engine_version: str
    generated_at: str
    clean_quality: QualityMetrics
    ambiguous_quality: QualityMetrics
    performance: tuple[PerformanceRecord, ...]

    def render_markdown(self) -> str:
        """Render the report as Markdown."""
        lines = [
            "# Reconciliation Benchmark Report",
            "",
            f"- Engine version: `{self.engine_version}`",
            f"- Generated at: {self.generated_at}",
            "",
            "## Quality (labeled corpus)",
            "",
            f"- Cases (clean): {self.clean_quality.cases_evaluated}",
            f"- Match precision / recall: "
            f"{self.clean_quality.match_precision:.3f} / {self.clean_quality.match_recall:.3f}",
            f"- Deterministic consistency: {self.clean_quality.deterministic_consistency}",
            "",
            "| Operation | Precision | Recall |",
            "|---|---:|---:|",
        ]
        for score in self.clean_quality.operation_scores:
            lines.append(
                f"| {score.operation_type} | {score.precision:.3f} | {score.recall:.3f} |"
            )
        lines += [
            "",
            f"- Ambiguity rate (repeated-structure corpus): "
            f"{self.ambiguous_quality.ambiguity_rate:.3f}",
            "",
            "## Performance (synthetic scenarios)",
            "",
            "| Scenario | Source | Target | Duration (ms) | Candidates | Peak (KB) | Ops |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for record in self.performance:
            lines.append(
                f"| {record.scenario} | {record.source_node_count} | "
                f"{record.target_node_count} | {record.duration_ms:.1f} | "
                f"{record.candidate_count} | {record.peak_memory_kb:.0f} | "
                f"{record.operation_count} |"
            )
        lines += [
            "",
            "_Measured facts only. No production thresholds are declared "
            "validated; a labeled calibration corpus remains an open question._",
            "",
        ]
        return "\n".join(lines)


def build_benchmark_report() -> BenchmarkReport:
    """Run the quality and performance benchmarks and assemble a report."""
    performance = (
        measure_performance("wide-200", wide_tree("s", 200), wide_tree("t", 200)),
        measure_performance("deep-80", deep_tree("s", 80), deep_tree("t", 80)),
        measure_performance("repetitive-20", repetitive_tree("s", 20), repetitive_tree("t", 20)),
        measure_performance("high-edit-120", *high_edit_density_pair(120)),
    )
    return BenchmarkReport(
        engine_version=ENGINE_VERSION,
        generated_at=datetime.now(UTC).isoformat(),
        clean_quality=evaluate_quality(clean_cases()),
        ambiguous_quality=evaluate_quality(ambiguous_cases()),
        performance=performance,
    )
