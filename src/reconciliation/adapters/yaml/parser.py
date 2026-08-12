"""Bounded YAML parsing for untrusted input."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from math import isfinite
from typing import Any

from reconciliation.adapters.yaml.errors import InputParseError, UnsafeYamlError


@dataclass(frozen=True)
class YamlSecurityLimits:
    """Bounds enforced on untrusted YAML input."""

    max_bytes: int = 10_000_000
    max_depth: int = 100
    max_nodes: int = 100_000


class SecureYamlParser:
    """Parse a conservative YAML data document under strict limits."""

    def __init__(self, limits: YamlSecurityLimits | None = None) -> None:
        self._limits = limits or YamlSecurityLimits()

    def parse(self, data: str | bytes, *, document_uri: str | None = None) -> object:
        """Parse YAML into standard JSON-like Python data structures."""
        raw = data.encode("utf-8") if isinstance(data, str) else data
        if len(raw) > self._limits.max_bytes:
            raise UnsafeYamlError(
                "YAML input exceeds the configured maximum size",
                location=document_uri,
                context={"bytes": len(raw), "limit": self._limits.max_bytes},
            )
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InputParseError(
                "YAML input is not valid UTF-8",
                location=document_uri,
                context={"detail": str(exc)},
            ) from exc
        yaml = _import_yaml()
        self._reject_unsupported_tokens(yaml, text, document_uri)
        try:
            documents = list(yaml.safe_load_all(text))
        except yaml.YAMLError as exc:
            raise InputParseError(
                "input is not well-formed YAML",
                location=document_uri,
                context={"detail": str(exc)},
            ) from exc
        if len(documents) > 1:
            raise UnsafeYamlError(
                "YAML multi-document streams are not supported",
                location=document_uri,
                context={"document_count": len(documents)},
            )
        parsed = documents[0] if documents else None
        self._enforce_structure_limits(parsed, document_uri)
        return parsed

    def _reject_unsupported_tokens(
        self, yaml: Any, text: str, document_uri: str | None
    ) -> None:
        try:
            tokens = list(yaml.scan(text))
        except yaml.YAMLError as exc:
            raise InputParseError(
                "input is not well-formed YAML",
                location=document_uri,
                context={"detail": str(exc)},
            ) from exc
        for token in tokens:
            if isinstance(token, yaml.tokens.AnchorToken):
                raise UnsafeYamlError(
                    "YAML anchors are not supported",
                    location=document_uri,
                    context={"anchor": token.value},
                )
            if isinstance(token, yaml.tokens.AliasToken):
                raise UnsafeYamlError(
                    "YAML aliases are not supported",
                    location=document_uri,
                    context={"alias": token.value},
                )
            if isinstance(token, yaml.tokens.TagToken):
                raise UnsafeYamlError(
                    "YAML custom tags are not supported",
                    location=document_uri,
                    context={"tag": str(token.value)},
                )
            if (
                isinstance(token, yaml.tokens.ScalarToken)
                and token.value == "<<"
            ):
                raise UnsafeYamlError(
                    "YAML merge keys are not supported",
                    location=document_uri,
                )

    def _enforce_structure_limits(self, value: object, document_uri: str | None) -> None:
        count = 0

        def walk(current: object, depth: int) -> None:
            nonlocal count
            count += 1
            if count > self._limits.max_nodes:
                raise UnsafeYamlError(
                    "YAML input exceeds the configured maximum node count",
                    location=document_uri,
                    context={"limit": self._limits.max_nodes},
                )
            if depth > self._limits.max_depth:
                raise UnsafeYamlError(
                    "YAML input exceeds the configured maximum nesting depth",
                    location=document_uri,
                    context={"limit": self._limits.max_depth},
                )
            if isinstance(current, dict):
                for key, child in current.items():
                    if not isinstance(key, str):
                        raise UnsafeYamlError(
                            "YAML mapping keys must be strings",
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
                raise UnsafeYamlError(
                    "YAML non-finite numeric values are not supported",
                    location=document_uri,
                )
            if isinstance(current, datetime | date):
                raise UnsafeYamlError(
                    "YAML timestamp values are not supported by the generic data adapter",
                    location=document_uri,
                )
            if current is not None and not isinstance(current, str | int | float | bool):
                raise UnsafeYamlError(
                    "YAML value has an unsupported type",
                    location=document_uri,
                    context={"python_type": type(current).__name__},
                )

        walk(value, 1)


def _import_yaml() -> Any:
    try:
        import yaml
    except ImportError as exc:
        raise InputParseError(
            "PyYAML is required to parse YAML documents",
            context={"missing": "yaml"},
        ) from exc
    return yaml
