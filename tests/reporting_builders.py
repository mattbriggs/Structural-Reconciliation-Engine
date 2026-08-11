"""Test helpers for the reporting layer."""

from __future__ import annotations

from reconciliation.application.contracts.localization import LocalizationValidationResult
from reconciliation.core.contracts.tree import CanonicalTree
from reconciliation.reporting.contracts import ReportOptions, ReportTable
from reconciliation.reporting.rows import build_report_table
from tests.app_builders import localize


def localize_and_table(
    source: CanonicalTree,
    target: CanonicalTree,
    *,
    options: ReportOptions | None = None,
    **localize_kwargs: object,
) -> tuple[LocalizationValidationResult, ReportTable]:
    """Reconcile, interpret, and flatten to a report table in one call."""
    result = localize(source, target, **localize_kwargs)  # type: ignore[arg-type]
    table = build_report_table(
        result, source_tree=source, locale_tree=target, options=options
    )
    return result, table
