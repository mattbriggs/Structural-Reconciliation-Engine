"""Tests for the CLI: exit-code policy, outputs, machine errors (REQ-183-185)."""

from __future__ import annotations

import io
import json
from pathlib import Path

from reconciliation.delivery.cli.app import run_cli

SRC = '<map><topicref keys="intro" href="i.dita"/><topicref keys="gone" href="g.dita"/></map>'
LOC = '<map><topicref keys="intro" href="i.dita"/></map>'
CLEAN_LOC = '<map><topicref keys="intro" href="i.dita"/></map>'


def _write(tmp_path: Path) -> tuple[Path, Path]:
    src = tmp_path / "s.ditamap"
    loc = tmp_path / "l.ditamap"
    src.write_text(SRC, encoding="utf-8")
    loc.write_text(LOC, encoding="utf-8")
    return src, loc


def test_findings_yield_content_exit_code(tmp_path: Path) -> None:
    # REQ-184: a detected content finding (MISSING is ERROR) is distinct from a
    # technical failure -> exit code 2.
    src, loc = _write(tmp_path)
    code = run_cli(source=src, locale=loc, locale_code="fr-FR", out=io.StringIO())
    assert code == 2


def test_report_only_mode_exits_zero(tmp_path: Path) -> None:
    src, loc = _write(tmp_path)
    code = run_cli(
        source=src, locale=loc, locale_code="fr-FR",
        treat_findings_as_failure=False, out=io.StringIO(),
    )
    assert code == 0


def test_technical_failure_exit_code_and_machine_error(tmp_path: Path) -> None:
    # REQ-183/185: missing input is a technical failure with machine output.
    out = io.StringIO()
    code = run_cli(
        source=tmp_path / "missing.ditamap",
        locale=tmp_path / "also-missing.ditamap",
        locale_code="fr-FR",
        machine_errors=True,
        out=out,
    )
    assert code == 1
    payload = json.loads(out.getvalue())
    assert payload["error"]["code"] == "INVALID_INPUT"


def test_writes_requested_artifacts(tmp_path: Path) -> None:
    src, loc = _write(tmp_path)
    csv_path = tmp_path / "r.csv"
    json_path = tmp_path / "r.json"
    html_path = tmp_path / "r.html"
    run_cli(
        source=src, locale=loc, locale_code="fr-FR",
        csv=csv_path, json_out=json_path, html=html_path, out=io.StringIO(),
    )
    assert csv_path.read_text(encoding="utf-8").startswith("job_id,")
    assert json.loads(json_path.read_text(encoding="utf-8"))["job_id"]
    assert "<main>" in html_path.read_text(encoding="utf-8")


def test_unknown_profile_is_technical_failure(tmp_path: Path) -> None:
    src, loc = _write(tmp_path)
    out = io.StringIO()
    code = run_cli(
        source=src, locale=loc, locale_code="fr-FR",
        document_profile="does-not-exist", machine_errors=True, out=out,
    )
    assert code == 1
    assert json.loads(out.getvalue())["error"]["code"] == "UNSUPPORTED_CONTRACT"
