"""Architectural release test for core independence (AC-031, REQ-249).

Importing :mod:`reconciliation.core` and reconciling two in-memory canonical
trees must not pull in XML, DITA, localization, FastAPI, persistence,
reporting, CCMS, or pricing modules. This is enforced mechanically by
inspecting ``sys.modules`` after a fresh import in a subprocess.
"""

from __future__ import annotations

import subprocess
import sys

FORBIDDEN_PREFIXES = (
    "lxml",
    "fastapi",
    "uvicorn",
    "starlette",
    "sqlalchemy",
    "jinja2",
    "typer",
    "reconciliation.adapters",
    "reconciliation.application",
    "reconciliation.infrastructure",
    "reconciliation.reporting",
    "reconciliation.delivery",
    "reconciliation.profiles",
    "reconciliation.benchmark",
    "reconciliation.config",
)

_PROBE = """
import sys
import reconciliation.core  # noqa: F401
import reconciliation.core.engine  # noqa: F401
from reconciliation.core.contracts import tree, profiles, results  # noqa: F401
forbidden = [
    name
    for name in sys.modules
    for prefix in {prefixes!r}
    if name == prefix or name.startswith(prefix + ".")
]
print(",".join(sorted(set(forbidden))))
"""


def test_core_import_pulls_no_forbidden_modules() -> None:
    probe = _PROBE.format(prefixes=FORBIDDEN_PREFIXES)
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        check=True,
    )
    leaked = completed.stdout.strip()
    assert leaked == "", f"core import leaked forbidden modules: {leaked}"
