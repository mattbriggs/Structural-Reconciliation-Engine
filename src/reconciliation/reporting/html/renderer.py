"""Self-contained HTML report renderer (REQ-134-147, REQ-237-242).

Renders a single, self-contained HTML document with embedded (local) CSS and
vanilla JavaScript — no external network dependency (REQ-146). Content is HTML
escaped by Jinja2 autoescaping (REQ-147, AC-026); the only markup marked safe
is the report's own stylesheet and script, read from packaged static assets.

The embedded script implements presentation state only (filter/sort/expand); it
never modifies the embedded engine data (report state is client-side only).
"""

from __future__ import annotations

import importlib.resources

from jinja2 import Environment, StrictUndefined, select_autoescape
from markupsafe import Markup

from reconciliation.application.contracts.localization import LocalizationValidationResult
from reconciliation.core.contracts.tree import CanonicalTree
from reconciliation.reporting.contracts import ReportOptions
from reconciliation.reporting.errors import ReportGenerationError
from reconciliation.reporting.html.view_model import build_view_model
from reconciliation.reporting.rows import build_report_table

_PACKAGE = "reconciliation.reporting.html"


def _asset(relative: str) -> str:
    return (
        importlib.resources.files(_PACKAGE).joinpath(relative).read_text(encoding="utf-8")
    )


class HtmlReportRenderer:
    """Renders a localization result to a self-contained HTML document."""

    media_type = "text/html"

    def __init__(self) -> None:
        self._env = Environment(
            autoescape=select_autoescape(default=True, default_for_string=True),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._template = self._env.from_string(_asset("templates/report.html.j2"))

    def render(
        self,
        result: LocalizationValidationResult,
        *,
        source_tree: CanonicalTree | None = None,
        locale_tree: CanonicalTree | None = None,
        options: ReportOptions | None = None,
    ) -> str:
        """Render the localization result to an HTML string.

        :param result: The localization validation result.
        :param source_tree: Source tree for paths (optional).
        :param locale_tree: Locale tree for paths (optional).
        :param options: Report options (redaction, suppressed inclusion).
        :returns: A self-contained HTML document.
        :raises ReportGenerationError: If rendering fails.
        """
        try:
            table = build_report_table(
                result,
                source_tree=source_tree,
                locale_tree=locale_tree,
                options=options or ReportOptions(),
            )
            view = build_view_model(result, table)
            return self._template.render(
                report=view,
                embedded_css=Markup(_asset("static/report.css")),
                embedded_js=Markup(_asset("static/report.js")),
            )
        except ReportGenerationError:
            raise
        except Exception as exc:
            raise ReportGenerationError(
                "failed to render HTML report", context={"detail": str(exc)}
            ) from exc
