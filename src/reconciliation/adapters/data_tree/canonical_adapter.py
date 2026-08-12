"""Canonicalization for parsed JSON/YAML-style data trees.

JSON and YAML both reduce to a small data model: mappings, sequences, scalars,
and null. This adapter maps that model to the domain-neutral ``CanonicalTree``
contract using shared ``data:*`` node types so equivalent JSON and YAML inputs
can produce compatible trees.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite
from typing import Any

from reconciliation.adapters.data_tree.errors import DataTreeAdaptationError
from reconciliation.core.contracts.tree import (
    CanonicalNode,
    CanonicalTree,
    CanonicalValue,
    SourceLocation,
)
from reconciliation.version import CANONICAL_TREE_CONTRACT_VERSION

type JsonLikeValue = (
    Mapping[str, Any] | Sequence[Any] | str | int | float | bool | None
)


def _node_type_for_scalar(value: object) -> str:
    if value is None:
        return "data:null"
    if isinstance(value, bool):
        return "data:boolean"
    if isinstance(value, str):
        return "data:string"
    if isinstance(value, int | float):
        return "data:number"
    raise DataTreeAdaptationError(
        "parsed data contains an unsupported scalar value",
        context={"python_type": type(value).__name__},
    )


def _canonical_scalar(value: object) -> CanonicalValue:
    if isinstance(value, float) and not isfinite(value):
        raise DataTreeAdaptationError("non-finite numeric values are not supported")
    if value is None or isinstance(value, str | int | float | bool):
        return value
    raise DataTreeAdaptationError(
        "parsed data contains a non-canonical scalar value",
        context={"python_type": type(value).__name__},
    )


def _scalar_content(value: object) -> dict[str, CanonicalValue]:
    canonical = _canonical_scalar(value)
    content: dict[str, CanonicalValue] = {"value": canonical}
    if canonical is not None:
        content["text"] = str(canonical)
    return content


def _path_child(parent_path: str, key_or_index: str | int) -> str:
    if isinstance(key_or_index, int):
        return f"{parent_path}[{key_or_index}]"
    escaped = key_or_index.replace("\\", "\\\\").replace('"', '\\"')
    if key_or_index.isidentifier():
        return f"{parent_path}.{key_or_index}"
    return f'{parent_path}["{escaped}"]'


def _is_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray)


def _is_container(value: object) -> bool:
    return isinstance(value, Mapping) or _is_sequence(value)


class DataTreeAdapter:
    """Adapt parsed JSON/YAML-like values into ``CanonicalTree``.

    :param contract_version: Canonical tree contract version to stamp on output.
    :param source_format: Format label recorded in tree metadata.
    """

    def __init__(
        self,
        *,
        contract_version: str = CANONICAL_TREE_CONTRACT_VERSION,
        source_format: str,
    ) -> None:
        self._contract_version = contract_version
        self._source_format = source_format

    def adapt(
        self,
        value: JsonLikeValue,
        *,
        tree_id: str,
        document_uri: str | None = None,
    ) -> CanonicalTree:
        """Adapt a parsed data value into a canonical tree."""
        nodes: dict[str, CanonicalNode] = {}
        try:
            child_ref = "n.0"
            nodes["n"] = CanonicalNode(
                node_ref="n",
                node_type="data:document",
                child_refs=(child_ref,),
                structural_properties={"format": self._source_format},
                source_location=SourceLocation(document_uri=document_uri, xpath="$"),
            )
            self._build_value(
                value,
                ref=child_ref,
                parent_ref="n",
                path="$",
                nodes=nodes,
                document_uri=document_uri,
            )
            metadata: dict[str, CanonicalValue] = {"format": self._source_format}
            if document_uri:
                metadata["document_uri"] = document_uri
            return CanonicalTree(
                contract_version=self._contract_version,
                tree_id=tree_id,
                root_node_ref="n",
                nodes=nodes,
                metadata=metadata,
            )
        except DataTreeAdaptationError:
            raise
        except Exception as exc:
            raise DataTreeAdaptationError(
                "failed to adapt parsed data into a canonical tree",
                location=document_uri,
                context={"detail": str(exc)},
            ) from exc

    def _build_value(
        self,
        value: object,
        *,
        ref: str,
        parent_ref: str,
        path: str,
        nodes: dict[str, CanonicalNode],
        document_uri: str | None,
    ) -> None:
        if isinstance(value, Mapping):
            self._build_object(value, ref, parent_ref, path, nodes, document_uri)
            return
        if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
            self._build_array(value, ref, parent_ref, path, nodes, document_uri)
            return
        nodes[ref] = CanonicalNode(
            node_ref=ref,
            node_type=_node_type_for_scalar(value),
            parent_ref=parent_ref,
            content_properties=_scalar_content(value),
            source_location=SourceLocation(document_uri=document_uri, xpath=path),
        )

    def _build_object(
        self,
        value: Mapping[object, object],
        ref: str,
        parent_ref: str,
        path: str,
        nodes: dict[str, CanonicalNode],
        document_uri: str | None,
    ) -> None:
        entries = list(value.items())
        for key, _child_value in entries:
            if not isinstance(key, str):
                raise DataTreeAdaptationError(
                    "data object keys must be strings",
                    location=document_uri,
                    context={"key_type": type(key).__name__, "path": path},
                )
        child_refs = tuple(f"{ref}.{index}" for index in range(len(entries)))
        nodes[ref] = CanonicalNode(
            node_ref=ref,
            node_type="data:object",
            parent_ref=parent_ref,
            child_refs=child_refs,
            source_location=SourceLocation(document_uri=document_uri, xpath=path),
        )
        for index, (key, child_value) in enumerate(entries):
            assert isinstance(key, str)
            property_ref = f"{ref}.{index}"
            value_ref = f"{property_ref}.0"
            child_path = _path_child(path, key)
            child_refs = (value_ref,) if _is_container(child_value) else ()
            content = {} if child_refs else _scalar_content(child_value)
            nodes[property_ref] = CanonicalNode(
                node_ref=property_ref,
                node_type="data:property",
                parent_ref=ref,
                child_refs=child_refs,
                identity_properties={"key": key},
                content_properties=content,
                structural_properties={"key": key},
                source_location=SourceLocation(document_uri=document_uri, xpath=child_path),
            )
            if child_refs:
                self._build_value(
                    child_value,
                    ref=value_ref,
                    parent_ref=property_ref,
                    path=child_path,
                    nodes=nodes,
                    document_uri=document_uri,
                )

    def _build_array(
        self,
        value: Sequence[object],
        ref: str,
        parent_ref: str,
        path: str,
        nodes: dict[str, CanonicalNode],
        document_uri: str | None,
    ) -> None:
        child_refs = tuple(f"{ref}.{index}" for index in range(len(value)))
        nodes[ref] = CanonicalNode(
            node_ref=ref,
            node_type="data:array",
            parent_ref=parent_ref,
            child_refs=child_refs,
            source_location=SourceLocation(document_uri=document_uri, xpath=path),
        )
        for index, child_value in enumerate(value):
            item_ref = f"{ref}.{index}"
            value_ref = f"{item_ref}.0"
            child_path = _path_child(path, index)
            child_refs = (value_ref,) if _is_container(child_value) else ()
            content = {} if child_refs else _scalar_content(child_value)
            nodes[item_ref] = CanonicalNode(
                node_ref=item_ref,
                node_type="data:item",
                parent_ref=ref,
                child_refs=child_refs,
                content_properties=content,
                structural_properties={"index": index},
                source_location=SourceLocation(document_uri=document_uri, xpath=child_path),
            )
            if child_refs:
                self._build_value(
                    child_value,
                    ref=value_ref,
                    parent_ref=item_ref,
                    path=child_path,
                    nodes=nodes,
                    document_uri=document_uri,
                )
