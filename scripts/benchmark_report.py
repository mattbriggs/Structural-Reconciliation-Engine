#!/usr/bin/env python
"""Generate and print the reconciliation benchmark report as Markdown.

Usage::

    python scripts/benchmark_report.py            # print to stdout
    python scripts/benchmark_report.py out.md     # write to a file
"""

from __future__ import annotations

import sys
from pathlib import Path

from reconciliation.benchmark.report import build_benchmark_report


def main() -> int:
    markdown = build_benchmark_report().render_markdown()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(markdown, encoding="utf-8")
    else:
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
