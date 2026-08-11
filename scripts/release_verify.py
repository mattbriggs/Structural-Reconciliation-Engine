#!/usr/bin/env python
"""Release acceptance gate (plan §8).

Runs every release gate and prints a summary, exiting non-zero if any *required*
gate fails. Gates that need an unavailable tool (e.g. Docker) are reported as
SKIPPED, not FAILED, and never block the overall verdict on their own.

Usage::

    python scripts/release_verify.py            # run all gates
    python scripts/release_verify.py --fast     # skip pytest/mkdocs (lint+types)
    python scripts/release_verify.py --docker    # additionally build the image
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

#: Minimum line-coverage rates enforced per scope (plan §7).
OVERALL_MIN = 90.0
CORE_MIN = 95.0


@dataclass
class GateResult:
    name: str
    status: str  # PASS / FAIL / SKIP
    detail: str = ""

    @property
    def failed(self) -> bool:
        return self.status == "FAIL"


def _run(cmd: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)


def gate_ruff() -> GateResult:
    proc = _run([PY, "-m", "ruff", "check", "src", "tests", "scripts"])
    status = "PASS" if proc.returncode == 0 else "FAIL"
    return GateResult("ruff", status, proc.stdout.strip()[-200:])


def gate_mypy() -> GateResult:
    proc = _run([PY, "-m", "mypy", "src"])
    ok = proc.returncode == 0
    return GateResult("mypy (strict)", "PASS" if ok else "FAIL", proc.stdout.strip()[-200:])


def gate_pytest_coverage(coverage_json: Path) -> tuple[GateResult, GateResult]:
    env = {**os.environ, "COVERAGE_FILE": str(coverage_json.with_suffix(".data"))}
    proc = _run(
        [
            PY, "-m", "pytest", "-q",
            "--cov=src/reconciliation", "--cov-branch",
            f"--cov-report=json:{coverage_json}",
        ],
        env=env,
    )
    tail = proc.stdout.strip().splitlines()[-1:] if proc.stdout else []
    test_gate = GateResult(
        "pytest", "PASS" if proc.returncode == 0 else "FAIL", " ".join(tail)
    )
    cov_gate = _coverage_gate(coverage_json)
    return test_gate, cov_gate


def _coverage_gate(coverage_json: Path) -> GateResult:
    if not coverage_json.exists():
        return GateResult("coverage thresholds", "FAIL", "no coverage.json produced")
    data = json.loads(coverage_json.read_text())
    overall = data["totals"]["percent_covered"]
    core_stmts = core_covered = 0
    for path, info in data["files"].items():
        if "reconciliation/core/" in path.replace("\\", "/"):
            core_stmts += info["summary"]["num_statements"]
            core_covered += info["summary"]["covered_lines"]
    core = (core_covered / core_stmts * 100.0) if core_stmts else 100.0
    ok = overall >= OVERALL_MIN and core >= CORE_MIN
    return GateResult(
        "coverage thresholds",
        "PASS" if ok else "FAIL",
        f"overall {overall:.1f}% (>= {OVERALL_MIN}), core {core:.1f}% (>= {CORE_MIN})",
    )


def gate_mkdocs() -> GateResult:
    proc = _run([PY, "-m", "mkdocs", "build", "--strict"])
    return GateResult(
        "mkdocs --strict", "PASS" if proc.returncode == 0 else "FAIL",
        proc.stderr.strip().splitlines()[-1] if proc.returncode else "",
    )


def gate_benchmark(out_path: Path) -> GateResult:
    from reconciliation.benchmark.report import build_benchmark_report

    report = build_benchmark_report()
    out_path.write_text(report.render_markdown(), encoding="utf-8")
    quality = report.clean_quality
    ok = quality.match_precision == 1.0 and quality.deterministic_consistency
    return GateResult(
        "benchmark report", "PASS" if ok else "FAIL",
        f"written to {out_path.name}; match P/R "
        f"{quality.match_precision:.2f}/{quality.match_recall:.2f}",
    )


def gate_docker(build: bool) -> GateResult:
    if shutil.which("docker") is None:
        return GateResult("docker smoke", "SKIP", "docker not available")
    info = _run(["docker", "info"])
    if info.returncode != 0:
        return GateResult("docker smoke", "SKIP", "docker daemon not running")
    if not build:
        return GateResult("docker smoke", "SKIP", "run with --docker to build the image")
    proc = _run(["docker", "build", "-t", "structural-reconciliation:verify", "."])
    return GateResult(
        "docker smoke", "PASS" if proc.returncode == 0 else "FAIL",
        proc.stderr.strip().splitlines()[-1] if proc.returncode else "image built",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Release acceptance gate.")
    parser.add_argument("--fast", action="store_true", help="skip pytest and mkdocs")
    parser.add_argument("--docker", action="store_true", help="also build the container image")
    args = parser.parse_args()

    results: list[GateResult] = [gate_ruff(), gate_mypy()]
    with tempfile.TemporaryDirectory() as tmp:
        coverage_json = Path(tmp) / "coverage.json"
        if not args.fast:
            test_gate, cov_gate = gate_pytest_coverage(coverage_json)
            results += [test_gate, cov_gate]
            results.append(gate_mkdocs())
        # Written to the repo root (not docs/), so it does not break the strict
        # docs build, which rejects pages absent from the nav.
        results.append(gate_benchmark(ROOT / "benchmark-report.md"))
        results.append(gate_docker(args.docker))

    print("\nRelease acceptance gate\n" + "=" * 60)
    for r in results:
        print(f"  [{r.status:^4}] {r.name:<22} {r.detail}")
    failed = [r for r in results if r.failed]
    verdict = "NOT READY" if failed else "READY"
    print("=" * 60)
    print(f"Verdict: {verdict}" + (f" — {len(failed)} gate(s) failed" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
