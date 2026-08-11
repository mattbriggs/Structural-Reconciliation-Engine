"""Deterministic tree normalization (REQ-016-024).

Normalization produces a :class:`NormalizedTree` — a canonical tree whose
content values have had configured insignificant variation removed — plus a
trace mapping each change to the rule that authorized it (REQ-023). Identity,
structure, and preserved keys are never altered (REQ-022).

The normalized tree reuses the :class:`CanonicalTree` shape so downstream
stages remain simple; it is wrapped in a distinct type only to make the
pipeline contract explicit and prevent accidentally matching against an
un-normalized tree.
"""

from __future__ import annotations

import re

from reconciliation.core.contracts.base import StrictModel
from reconciliation.core.contracts.profiles import NormalizationProfile
from reconciliation.core.contracts.tree import CanonicalNode, CanonicalTree, CanonicalValue

_WHITESPACE = re.compile(r"\s+")


class NormalizationTraceEntry(StrictModel):
    """Records one normalization action for audit (REQ-023)."""

    node_ref: str
    property_key: str
    rule: str


class NormalizedTree(StrictModel):
    """A canonical tree after normalization, plus the action trace.

    :ivar tree: The normalized canonical tree.
    :ivar trace: Ordered normalization actions, each attributed to a rule.
    :ivar profile_version: Version of the normalization profile applied.
    """

    tree: CanonicalTree
    trace: tuple[NormalizationTraceEntry, ...] = ()
    profile_version: str


def _normalize_value(value: CanonicalValue) -> CanonicalValue:
    """Collapse whitespace in string values recursively."""
    if isinstance(value, str):
        return _WHITESPACE.sub(" ", value).strip()
    if isinstance(value, list):
        return [_normalize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _normalize_value(v) for k, v in value.items()}
    return value


class TreeNormalizerService:
    """Default :class:`TreeNormalizer` implementation.

    :param profile: Not stored; normalization is applied per-call so a single
        instance is reusable and stateless (supporting determinism, REQ-202).
    """

    def normalize(self, tree: CanonicalTree, profile: NormalizationProfile) -> NormalizedTree:
        """Return a normalized copy of ``tree`` under ``profile`` rules.

        :param tree: The validated canonical tree to normalize.
        :param profile: Normalization rules to apply.
        :returns: A :class:`NormalizedTree` with an attributed action trace.

        .. note::
           Only ``content_properties`` are normalized. Identity and structural
           properties are copied verbatim to honor REQ-022.
        """
        trace: list[NormalizationTraceEntry] = []
        new_nodes: dict[str, CanonicalNode] = {}

        for node_ref in sorted(tree.nodes):
            node = tree.nodes[node_ref]
            new_content: dict[str, CanonicalValue] = {}
            for key in sorted(node.content_properties):
                value = node.content_properties[key]
                if key in profile.nonsemantic_metadata_keys:
                    trace.append(
                        NormalizationTraceEntry(
                            node_ref=node_ref, property_key=key, rule="exclude-nonsemantic"
                        )
                    )
                    continue
                if profile.collapse_whitespace and key not in profile.preserve_property_keys:
                    normalized = _normalize_value(value)
                    if normalized != value:
                        trace.append(
                            NormalizationTraceEntry(
                                node_ref=node_ref,
                                property_key=key,
                                rule="collapse-whitespace",
                            )
                        )
                    new_content[key] = normalized
                else:
                    new_content[key] = value

            new_nodes[node_ref] = node.model_copy(update={"content_properties": new_content})

        normalized_tree = tree.model_copy(update={"nodes": new_nodes})
        return NormalizedTree(
            tree=normalized_tree,
            trace=tuple(trace),
            profile_version=profile.version,
        )
