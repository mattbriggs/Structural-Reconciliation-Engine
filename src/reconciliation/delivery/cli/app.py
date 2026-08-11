"""Typer CLI: ``reconcile-localization`` (REQ-183-185).

Adapts two documents, runs the pipeline, writes requested artifacts, and exits
with a code determined by the configurable :class:`ExitCodePolicy` — separating
technical failures from detected content findings. ``--machine-errors`` emits a
structured JSON error for automated callers (REQ-185).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, TextIO

import typer

from reconciliation.application.contracts.common import AuthoritativeSide
from reconciliation.application.contracts.jobs import ComparisonRequest, ComparisonState
from reconciliation.delivery.cli.exit_codes import ExitCodePolicy, resolve_exit_code
from reconciliation.delivery.composition import DEFAULT_PROFILE_ID, build_comparison_service
from reconciliation.reporting.csv_renderer import CsvReportRenderer
from reconciliation.reporting.html.renderer import HtmlReportRenderer
from reconciliation.reporting.json_renderer import JsonReportRenderer
from reconciliation.reporting.rows import build_report_table

app = typer.Typer(add_completion=False, help="Source-to-locale XML reconciliation.")


def run_cli(
    *,
    source: Path,
    locale: Path,
    locale_code: str,
    document_profile: str = DEFAULT_PROFILE_ID,
    html: Path | None = None,
    csv: Path | None = None,
    json_out: Path | None = None,
    machine_errors: bool = False,
    treat_findings_as_failure: bool = True,
    out: TextIO | None = None,
) -> int:
    """Run one comparison and return the process exit code.

    Separated from the Typer command so it is directly unit-testable.
    """
    stream: TextIO = out if out is not None else sys.stdout
    policy = ExitCodePolicy(treat_findings_as_failure=treat_findings_as_failure)
    try:
        source_content = source.read_text(encoding="utf-8")
        locale_content = locale.read_text(encoding="utf-8")
    except OSError as exc:
        return _emit_error(
            stream, machine_errors, "INVALID_INPUT", f"cannot read input: {exc}", policy
        )

    request = ComparisonRequest(
        source_content=source_content,
        locale_content=locale_content,
        locale=locale_code,
        document_profile_id=document_profile,
        authoritative_side=AuthoritativeSide.SOURCE,
    )
    outcome = build_comparison_service().run(request)
    record = outcome.record

    if record.state is not ComparisonState.COMPLETED or outcome.result is None:
        return _emit_error(
            stream,
            machine_errors,
            record.error_code or "COMPARISON_FAILED",
            record.error_message or "comparison did not complete",
            policy,
            correlation_id=record.correlation_id,
        )

    result = outcome.result
    table = build_report_table(result)
    if csv is not None:
        csv.write_text(CsvReportRenderer().render(table), encoding="utf-8")
    if json_out is not None:
        json_out.write_text(JsonReportRenderer().render_full(result, table), encoding="utf-8")
    if html is not None:
        html.write_text(HtmlReportRenderer().render(result), encoding="utf-8")

    if machine_errors:
        print(
            json.dumps(
                {"job_id": record.job_id, "state": record.state.value,
                 "status_counts": record.status_counts},
                ensure_ascii=False,
            ),
            file=stream,
        )
    else:
        print(f"Job {record.job_id} completed for locale {result.locale}.", file=stream)
        for status, count in sorted(result.summary.status_counts.items()):
            print(f"  {status}: {count}", file=stream)

    return resolve_exit_code(record, result, policy)


def _emit_error(
    stream: TextIO,
    machine_errors: bool,
    code: str,
    message: str,
    policy: ExitCodePolicy,
    *,
    correlation_id: str | None = None,
) -> int:
    if machine_errors:
        print(
            json.dumps(
                {"error": {"code": code, "message": message, "correlation_id": correlation_id}},
                ensure_ascii=False,
            ),
            file=stream,
        )
    else:
        print(f"error [{code}]: {message}", file=sys.stderr)
    return policy.technical_error


@app.command()
def reconcile(
    source: Annotated[Path, typer.Option(help="Source document path.")],
    locale: Annotated[Path, typer.Option(help="Locale document path.")],
    locale_code: Annotated[str, typer.Option(help="Locale code, e.g. fr-FR.")],
    document_profile: Annotated[
        str, typer.Option(help="Document profile id.")
    ] = DEFAULT_PROFILE_ID,
    html: Annotated[Path | None, typer.Option(help="Write an HTML report here.")] = None,
    csv: Annotated[Path | None, typer.Option(help="Write a CSV report here.")] = None,
    json_out: Annotated[
        Path | None, typer.Option("--json", help="Write a JSON result here.")
    ] = None,
    machine_errors: Annotated[
        bool, typer.Option(help="Emit machine-readable JSON output.")
    ] = False,
    treat_findings_as_failure: Annotated[
        bool, typer.Option(help="Exit non-zero when blocking findings exist.")
    ] = True,
) -> None:
    """Reconcile a source document against its localized counterpart."""
    code = run_cli(
        source=source,
        locale=locale,
        locale_code=locale_code,
        document_profile=document_profile,
        html=html,
        csv=csv,
        json_out=json_out,
        machine_errors=machine_errors,
        treat_findings_as_failure=treat_findings_as_failure,
    )
    raise typer.Exit(code)


def main() -> None:
    """Console-script entry point."""
    app()
