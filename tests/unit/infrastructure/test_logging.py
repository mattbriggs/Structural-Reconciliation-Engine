"""Tests for structured logging: redaction and correlation (REQ-220/221/245)."""

from __future__ import annotations

import io
import json
from collections.abc import Iterator

import pytest
import structlog

from reconciliation.infrastructure.logging import (
    bound_correlation,
    configure_logging,
    get_logger,
    redact_mapping,
)


@pytest.fixture(autouse=True)
def _reset_structlog() -> Iterator[None]:
    yield
    structlog.reset_defaults()


def test_redact_mapping_masks_sensitive_and_content() -> None:
    result = redact_mapping(
        {
            "password": "hunter2",
            "source_content": "<map/>",
            "job_id": "j-1",
            "nested": {"token": "abc", "count": 3},
        },
        redact_content=True,
    )
    assert result["password"] == "[REDACTED]"
    assert result["source_content"] == "[REDACTED]"
    assert result["job_id"] == "j-1"
    assert result["nested"]["token"] == "[REDACTED]"
    assert result["nested"]["count"] == 3


def test_redact_mapping_keeps_content_when_disabled_but_masks_credentials() -> None:
    result = redact_mapping(
        {"password": "x", "text": "hello world"}, redact_content=False
    )
    # Credentials are ALWAYS masked (REQ-220); content only when enabled (REQ-221).
    assert result["password"] == "[REDACTED]"
    assert result["text"] == "hello world"


def test_configured_logging_redacts_and_correlates() -> None:
    stream = io.StringIO()
    configure_logging(json_output=True, redact_content=True, stream=stream)
    logger = get_logger("test")
    with bound_correlation("corr-xyz"):
        logger.info("event.happened", source_content="SECRET", password="p", node_count=5)
    event = json.loads(stream.getvalue().strip().splitlines()[-1])
    assert event["correlation_id"] == "corr-xyz"
    assert event["source_content"] == "[REDACTED]"
    assert event["password"] == "[REDACTED]"
    assert event["node_count"] == 5
    assert event["event"] == "event.happened"
    assert event["level"] == "info"


def test_correlation_is_scoped_to_context() -> None:
    stream = io.StringIO()
    configure_logging(json_output=True, stream=stream)
    logger = get_logger("test")
    with bound_correlation("inside"):
        logger.info("in")
    logger.info("out")
    lines = [json.loads(line) for line in stream.getvalue().strip().splitlines()]
    assert lines[0]["correlation_id"] == "inside"
    assert "correlation_id" not in lines[1]
