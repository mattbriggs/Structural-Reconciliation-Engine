"""Bounded JSON parsing for untrusted input."""

from __future__ import annotations

import json
from dataclasses import dataclass
from math import isfinite
from typing import Any

from reconciliation.adapters.json.errors import InputParseError, UnsafeJsonError


@dataclass(frozen=True)
class JsonSecurityLimits:
    """Bounds enforced on untrusted JSON input."""

    max_bytes: int = 10_000_000
    max_depth: int = 100
    max_nodes: int = 100_000


class SecureJsonParser:
    """Parse JSON with deterministic size, depth, and node-count limits."""

    def __init__(self, limits: JsonSecurityLimits | None = None) -> None:
        self._limits = limits or JsonSecurityLimits()

    def parse(self, data: str | bytes, *, document_uri: str | None = None) -> object:
        """Parse JSON into standard Python data structures."""
        raw = data.encode("utf-8") if isinstance(data, str) else data
        if len(raw) > self._limits.max_bytes:
            raise UnsafeJsonError(
                "JSON input exceeds the configured maximum size",
                location=document_uri,
                context={"bytes": len(raw), "limit": self._limits.max_bytes},
            )
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InputParseError(
                "JSON input is not valid UTF-8",
                location=document_uri,
                context={"detail": str(exc)},
            ) from exc
        try:
            parsed = json.loads(
                text,
                parse_constant=lambda value: (_raise_invalid_constant(value)),
            )
        except json.JSONDecodeError as exc:
            raise InputParseError(
                "input is not well-formed JSON",
                location=document_uri,
                context={"detail": str(exc)},
            ) from exc
        self._enforce_structure_limits(parsed, document_uri)
        return parsed

    def _enforce_structure_limits(self, value: object, document_uri: str | None) -> None:
        count = 0

        def walk(current: object, depth: int) -> None:
            nonlocal count
            count += 1
            if count > self._limits.max_nodes:
                raise UnsafeJsonError(
                    "JSON input exceeds the configured maximum node count",
                    location=document_uri,
                    context={"limit": self._limits.max_nodes},
                )
            if depth > self._limits.max_depth:
                raise UnsafeJsonError(
                    "JSON input exceeds the configured maximum nesting depth",
                    location=document_uri,
                    context={"limit": self._limits.max_depth},
                )
            if isinstance(current, dict):
                for key, child in current.items():
                    if not isinstance(key, str):
                        raise UnsafeJsonError(
                            "JSON object keys must be strings",
                            location=document_uri,
                            context={"key_type": type(key).__name__},
                        )
                    walk(child, depth + 1)
                return
            if isinstance(current, list):
                for child in current:
                    walk(child, depth + 1)
                return
            if isinstance(current, float) and not isfinite(current):
                raise UnsafeJsonError(
                    "JSON non-finite numeric values are not supported",
                    location=document_uri,
                )
            if current is not None and not isinstance(current, str | int | float | bool):
                raise UnsafeJsonError(
                    "JSON value has an unsupported type",
                    location=document_uri,
                    context={"python_type": type(current).__name__},
                )

        walk(value, 1)


def _raise_invalid_constant(value: str) -> Any:
    raise json.JSONDecodeError(f"invalid JSON constant {value}", value, 0)
