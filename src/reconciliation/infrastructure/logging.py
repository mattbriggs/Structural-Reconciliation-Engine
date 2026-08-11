"""Structured logging with redaction and correlation (REQ-220/221/243/245).

Configures ``structlog`` to emit structured events that:

* carry a correlation id bound via context vars, propagated across application,
  adapter, and reporting logs (REQ-245);
* never include credentials (always masked) or content values (masked unless a
  controlled environment enables content in logs) (REQ-220, REQ-221, REQ-243).

The redaction logic is exposed as a pure function so it is directly testable,
and installed as a structlog processor so it applies to every event.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Iterator
from typing import Any, TextIO, cast

import structlog

#: Keys whose values are ALWAYS masked, regardless of content settings — these
#: carry credentials/secrets that must never appear in logs (REQ-220).
SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "authorization",
        "credential",
        "credentials",
        "access_key",
        "private_key",
    }
)

#: Keys carrying source or translated *content*; masked unless content logging
#: is explicitly enabled (REQ-221).
CONTENT_KEYS: frozenset[str] = frozenset(
    {
        "content",
        "source_content",
        "locale_content",
        "text",
        "navtitle",
        "title",
        "label",
        "source_label",
        "locale_label",
        "message",
    }
)

_MASK = "[REDACTED]"


def redact_mapping(data: dict[str, Any], *, redact_content: bool) -> dict[str, Any]:
    """Return a copy of ``data`` with sensitive/content values masked.

    :param data: The event mapping.
    :param redact_content: When True, content-bearing keys are also masked.
    :returns: A new mapping; nested mappings are redacted recursively.
    """
    result: dict[str, Any] = {}
    for key, value in data.items():
        lowered = key.lower()
        if lowered in SENSITIVE_KEYS or (redact_content and lowered in CONTENT_KEYS):
            result[key] = _MASK
        elif isinstance(value, dict):
            result[key] = redact_mapping(value, redact_content=redact_content)
        else:
            result[key] = value
    return result


def redaction_processor(
    *, redact_content: bool
) -> structlog.types.Processor:
    """Return a structlog processor that redacts each event (REQ-220, REQ-221)."""

    def _processor(
        _logger: Any, _method: str, event_dict: structlog.types.EventDict
    ) -> structlog.types.EventDict:
        return redact_mapping(dict(event_dict), redact_content=redact_content)

    return _processor


def configure_logging(
    *,
    level: str = "INFO",
    json_output: bool = True,
    redact_content: bool = True,
    stream: TextIO | None = None,
) -> None:
    """Configure structlog for the process.

    :param level: Logging level name.
    :param json_output: Emit JSON (vs. console-rendered) logs.
    :param redact_content: Redact content-bearing fields (REQ-221).
    :param stream: Optional output stream (used by tests).
    """
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer(colors=False)
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            redaction_processor(redact_content=redact_content),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping().get(level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(file=stream),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str | None = None) -> structlog.types.FilteringBoundLogger:
    """Return a bound structlog logger."""
    return cast("structlog.types.FilteringBoundLogger", structlog.get_logger(name))


@contextlib.contextmanager
def bound_correlation(correlation_id: str | None) -> Iterator[None]:
    """Bind a correlation id for all logs emitted within the context (REQ-245)."""
    if correlation_id is None:
        yield
        return
    tokens = structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    try:
        yield
    finally:
        structlog.contextvars.reset_contextvars(**tokens)


def emit_observability(
    logger: structlog.types.FilteringBoundLogger, report: Any
) -> None:
    """Log a comparison's stage timings and outcome counts (REQ-243-246).

    :param logger: A bound structlog logger.
    :param report: An :class:`ObservabilityReport`. Only counts/timings are
        logged — never content — so this is safe to emit by default (REQ-243).
    """
    from reconciliation.application.contracts.observability import ObservabilityReport

    assert isinstance(report, ObservabilityReport)
    with bound_correlation(report.correlation_id):
        for stage, duration_ms in report.stage_durations_ms.items():
            logger.info("comparison.stage", stage=stage, duration_ms=duration_ms)
        logger.info(
            "comparison.outcome",
            job_id=report.job_id,
            outcome=report.outcome,
            technical_failure=report.technical_failure,
            completed_with_issues=report.completed_with_issues,
            source_node_count=report.source_node_count,
            target_node_count=report.target_node_count,
            candidate_count=report.candidate_count,
            match_count=report.match_count,
            ambiguity_count=report.ambiguity_count,
            operation_count=report.operation_count,
            suppression_count=report.suppression_count,
            recommendation_count=report.recommendation_count,
        )
