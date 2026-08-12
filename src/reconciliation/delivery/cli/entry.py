"""Console-script entry point for ``reconcile-localization`` (REQ-183-185).

The CLI is an *optional* delivery layer. It needs ``typer``, and its default
document-profile path additionally needs the XML/DITA parser, the YAML profile
loader, and the HTML report renderer. The base install stays core-only on
purpose, so the packaging story must not pretend otherwise: this shim imports
the CLI lazily and turns a missing extra into one actionable line instead of a
bare :class:`ModuleNotFoundError` traceback.
"""

from __future__ import annotations

#: How to obtain everything the CLI needs.
CLI_EXTRA_HINT = 'install the CLI extra: pip install "structural-reconciliation[cli]"'


def main() -> None:
    """Run the CLI, or explain which optional dependency is missing."""
    try:
        from reconciliation.delivery.cli.app import app
    except ImportError as exc:
        missing = getattr(exc, "name", None) or "an optional dependency"
        raise SystemExit(
            f"reconcile-localization is unavailable: {missing} is not installed. "
            f"{CLI_EXTRA_HINT}"
        ) from exc
    app()
