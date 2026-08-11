"""CSV report renderer (REQ-148, REQ-153, REQ-154, AC-027).

Emits UTF-8 CSV with all applicable columns from the SRS §3.18 field table.
List-valued columns (evidence codes) are joined with ``;``; Booleans render as
``true``/``false``; absent values render as empty cells.
"""

from __future__ import annotations

import csv
import io
from typing import Any

from reconciliation.reporting.contracts import ReportTable


class CsvReportRenderer:
    """Renders a report table to UTF-8 CSV."""

    media_type = "text/csv"

    def render(self, table: ReportTable) -> str:
        """Render the report table to a CSV string.

        :param table: The report table.
        :returns: CSV text including a header row of all columns.
        """
        columns = ReportTable.columns()
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(columns)
        for row in table.rows:
            data = row.model_dump()
            writer.writerow([_cell(data[column]) for column in columns])
        return buffer.getvalue()


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ";".join(str(item) for item in value)
    return str(value)
