"""Unit tests for translation-state and locale-policy services."""

from __future__ import annotations

from reconciliation.application.contracts.localization import TranslationState
from reconciliation.application.contracts.policy import (
    LocaleVariationPolicy,
    LocaleVariationRule,
)
from reconciliation.application.services.locale_policy import LocaleVariationPolicyService
from reconciliation.application.services.translation_state import (
    TranslationStateConfig,
    TranslationStateService,
)
from reconciliation.core.contracts.profiles import OperationType
from reconciliation.core.contracts.tree import CanonicalNode


def _node(**content) -> CanonicalNode:
    return CanonicalNode(node_ref="n", node_type="topicref", content_properties=content)


def test_translation_state_current() -> None:
    service = TranslationStateService()
    src = _node(revision="5")
    loc = _node(**{"source-revision": "5"})
    assert service.state_for(src, loc) is TranslationState.CURRENT


def test_translation_state_stale() -> None:
    service = TranslationStateService()
    src = _node(revision="6")
    loc = _node(**{"source-revision": "5"})
    assert service.state_for(src, loc) is TranslationState.STALE


def test_translation_state_unknown_without_metadata() -> None:
    service = TranslationStateService()
    assert service.state_for(_node(), _node()) is TranslationState.UNKNOWN


def test_translation_state_custom_keys() -> None:
    service = TranslationStateService(
        TranslationStateConfig(source_revision_key="rev", locale_source_revision_key="srcrev")
    )
    src = _node(rev="2")
    loc = _node(srcrev="2")
    assert service.state_for(src, loc) is TranslationState.CURRENT


def test_locale_policy_exemption_matches() -> None:
    service = LocaleVariationPolicyService()
    policy = LocaleVariationPolicy(
        policy_id="p",
        version="v1",
        locale="fr-FR",
        rules=(
            LocaleVariationRule(
                rule_id="allow-insert",
                permitted_operation=OperationType.INSERT,
                node_types=frozenset({"topicref"}),
                justification="ok",
            ),
        ),
    )
    assert (
        service.exemption_for(policy, locale="fr-FR", operation=OperationType.INSERT, node_type="topicref")
        == "allow-insert"
    )
    # Wrong locale -> no exemption.
    assert (
        service.exemption_for(policy, locale="de-DE", operation=OperationType.INSERT, node_type="topicref")
        is None
    )
    # Wrong operation -> no exemption.
    assert (
        service.exemption_for(policy, locale="fr-FR", operation=OperationType.DELETE, node_type="topicref")
        is None
    )


def test_locale_policy_none_returns_no_exemption() -> None:
    service = LocaleVariationPolicyService()
    assert (
        service.exemption_for(None, locale="fr-FR", operation=OperationType.INSERT, node_type="x")
        is None
    )
