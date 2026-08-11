"""Translation-state assessment (REQ-110-116, AC-022-024).

Compares source revision metadata with the source revision a locale node was
last synchronized against, to decide whether a translation is current, stale,
or of unknown currency. When reliable lineage metadata is absent the state is
``UNKNOWN`` — the system never claims current or stale without evidence
(REQ-116, AC-023).
"""

from __future__ import annotations

from dataclasses import dataclass

from reconciliation.application.contracts.localization import TranslationState
from reconciliation.core.contracts.tree import CanonicalNode


@dataclass(frozen=True)
class TranslationStateConfig:
    """Property keys used to read revision lineage.

    :ivar source_revision_key: Property on the source node holding its revision.
    :ivar locale_source_revision_key: Property on the locale node holding the
        source revision the translation was based on.
    """

    source_revision_key: str = "revision"
    locale_source_revision_key: str = "source-revision"


class TranslationStateService:
    """Derives :class:`TranslationState` from node revision metadata.

    :param config: Property-key configuration; defaults to conventional keys.
    """

    def __init__(self, config: TranslationStateConfig | None = None) -> None:
        self._config = config or TranslationStateConfig()

    def state_for(
        self, source_node: CanonicalNode, locale_node: CanonicalNode
    ) -> TranslationState:
        """Assess the translation currency of a matched node pair.

        :param source_node: The source canonical node.
        :param locale_node: The corresponding locale canonical node.
        :returns: ``CURRENT`` when the locale was synced to the current source
            revision, ``STALE`` when the source has since advanced (AC-022),
            or ``UNKNOWN`` when lineage metadata is insufficient (AC-023).
        """
        source_rev = self._read(source_node, self._config.source_revision_key)
        synced_rev = self._read(locale_node, self._config.locale_source_revision_key)
        if source_rev is None or synced_rev is None:
            return TranslationState.UNKNOWN
        if source_rev == synced_rev:
            return TranslationState.CURRENT
        return TranslationState.STALE

    @staticmethod
    def _read(node: CanonicalNode, key: str) -> str | None:
        for bucket in (
            node.identity_properties,
            node.content_properties,
            node.structural_properties,
        ):
            value = bucket.get(key)
            if value is not None:
                return str(value)
        return None
