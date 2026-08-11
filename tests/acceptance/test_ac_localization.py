"""Acceptance tests AC-003, AC-017..024, AC-037..040 (localization + repair)."""

from __future__ import annotations

import pytest

from reconciliation.application.contracts.common import AuthoritativeSide
from reconciliation.application.contracts.localization import TranslationState
from reconciliation.application.contracts.policy import LocaleVariationPolicy, LocaleVariationRule
from reconciliation.core.contracts.profiles import OperationType
from tests.app_builders import issue_with_status, localize, statuses
from tests.builders import TreeBuilder

pytestmark = pytest.mark.acceptance


def _pair(source_children, locale_children):
    src = TreeBuilder("s", "r", node_type="map")
    for ref, kw in source_children:
        src.child("r", ref, **kw)
    tgt = TreeBuilder("t", "r", node_type="map")
    for ref, kw in locale_children:
        tgt.child("r", ref, **kw)
    return src.build(), tgt.build()


def test_ac_003_deleted_locale_node_is_missing_in_locale() -> None:
    src, tgt = _pair(
        [("a", {"identity": {"id": "a"}}), ("b", {"identity": {"id": "b"}})],
        [("a", {"identity": {"id": "a"}})],
    )
    result = localize(src, tgt)
    assert "MISSING_IN_LOCALE" in statuses(result)
    missing = issue_with_status(result, "MISSING_IN_LOCALE")
    assert missing.source_node_id == "b"


def test_ac_017_confirmed_source_to_locale_match() -> None:
    src, tgt = _pair(
        [("a", {"identity": {"id": "a"}})], [("a", {"identity": {"id": "a"}})]
    )
    result = localize(src, tgt)
    assert issue_with_status(result, "CONFIRMED_MATCH") is not None


def test_ac_018_probable_match_below_confirmed_threshold() -> None:
    # No ids: matched by partial similarity (score ~0.667) -> below the 0.9
    # confirmed threshold but above the match threshold -> PROBABLE_MATCH.
    # The source node has a child so its child-signature differs, lowering score.
    src_b = TreeBuilder("s", "r", node_type="map")
    src_b.child("r", "a", node_type="item", content={"t": "x"})
    src_b.child("a", "a1", node_type="leaf")
    tgt_b = TreeBuilder("t", "r", node_type="map")
    tgt_b.child("r", "b", node_type="item", content={"t": "x"})
    result = localize(src_b.build(), tgt_b.build())
    assert issue_with_status(result, "PROBABLE_MATCH") is not None


def test_ac_019_ambiguous_match_lists_alternatives() -> None:
    src, tgt = _pair(
        [
            ("s1", {"node_type": "item", "content": {"t": "x"}}),
            ("s2", {"node_type": "item", "content": {"t": "x"}}),
        ],
        [
            ("t1", {"node_type": "item", "content": {"t": "x"}}),
            ("t2", {"node_type": "item", "content": {"t": "x"}}),
        ],
    )
    result = localize(src, tgt)
    ambiguous = issue_with_status(result, "AMBIGUOUS_MATCH")
    assert ambiguous is not None
    assert len(ambiguous.core_match_ids) >= 2


def test_ac_020_wrong_parent() -> None:
    src = TreeBuilder("s", "r", node_type="map")
    src.child("r", "p1", identity={"id": "p1"}).child("r", "p2", identity={"id": "p2"})
    src.child("p1", "a", identity={"id": "a"})
    tgt = TreeBuilder("t", "r", node_type="map")
    tgt.child("r", "p1", identity={"id": "p1"}).child("r", "p2", identity={"id": "p2"})
    tgt.child("p2", "a", identity={"id": "a"})
    result = localize(src.build(), tgt.build())
    assert "WRONG_PARENT" in statuses(result)


def test_ac_021_locale_specific_exception_is_exempt() -> None:
    src, tgt = _pair(
        [("a", {"identity": {"id": "a"}})],
        [
            ("a", {"identity": {"id": "a"}}),
            ("note", {"node_type": "topicref", "identity": {"id": "note"}}),
        ],
    )
    policy = LocaleVariationPolicy(
        policy_id="fr-policy",
        version="v1",
        locale="fr-FR",
        rules=(
            LocaleVariationRule(
                rule_id="allow-extra-topicref",
                permitted_operation=OperationType.INSERT,
                node_types=frozenset({"topicref"}),
                justification="French locale may add a regulatory note.",
            ),
        ),
    )
    result = localize(src, tgt, locale="fr-FR", policy=policy)
    exempt = issue_with_status(result, "EXEMPT_LOCALE_VARIATION")
    assert exempt is not None
    assert exempt.policy_exemption == "allow-extra-topicref"
    # The exemption marks but does not remove the difference (REQ-106).
    assert "EXTRA_IN_LOCALE" not in statuses(result)


def test_ac_022_source_updated_when_revision_advanced() -> None:
    src, tgt = _pair(
        [("a", {"identity": {"id": "a"}, "content": {"revision": "3"}})],
        [("a", {"identity": {"id": "a"}, "content": {"source-revision": "2"}})],
    )
    result = localize(src, tgt)
    issue = issue_with_status(result, "SOURCE_UPDATED")
    assert issue is not None
    assert issue.translation_state is TranslationState.STALE


def test_ac_023_insufficient_metadata_is_unknown() -> None:
    src, tgt = _pair(
        [("a", {"identity": {"id": "a"}})], [("a", {"identity": {"id": "a"}})]
    )
    result = localize(src, tgt)
    confirmed = issue_with_status(result, "CONFIRMED_MATCH")
    assert confirmed is not None
    # No revision lineage -> state is UNKNOWN, never claimed current/stale.
    assert confirmed.translation_state is TranslationState.UNKNOWN
    assert "SOURCE_UPDATED" not in statuses(result)


def test_ac_024_translation_text_independence() -> None:
    # Same id, very different content (translated) -> still a confirmed match.
    src, tgt = _pair(
        [("a", {"identity": {"id": "a"}, "content": {"navtitle": "Introduction"}})],
        [("a", {"identity": {"id": "a"}, "content": {"navtitle": "Wprowadzenie"}})],
    )
    result = localize(src, tgt)
    statuses_present = statuses(result)
    assert "CONFIRMED_MATCH" in statuses_present
    assert "MISSING_IN_LOCALE" not in statuses_present
    assert "EXTRA_IN_LOCALE" not in statuses_present


def test_ac_037_no_recommendation_is_executable() -> None:
    src = TreeBuilder("s", "r", node_type="map")
    src.child("r", "p1", identity={"id": "p1"}).child("r", "p2", identity={"id": "p2"})
    src.child("p1", "a", identity={"id": "a"})
    tgt = TreeBuilder("t", "r", node_type="map")
    tgt.child("r", "p1", identity={"id": "p1"}).child("r", "p2", identity={"id": "p2"})
    tgt.child("p2", "a", identity={"id": "a"})
    result = localize(src.build(), tgt.build())
    assert result.recommendations
    assert all(not r.executable for r in result.recommendations)
    assert all(not r.auto_fix_eligible for r in result.recommendations)


def test_ac_038_no_recommendation_for_ambiguous_match() -> None:
    src, tgt = _pair(
        [
            ("s1", {"node_type": "item", "content": {"t": "x"}}),
            ("s2", {"node_type": "item", "content": {"t": "x"}}),
        ],
        [
            ("t1", {"node_type": "item", "content": {"t": "x"}}),
            ("t2", {"node_type": "item", "content": {"t": "x"}}),
        ],
    )
    result = localize(src, tgt)
    ambiguous = issue_with_status(result, "AMBIGUOUS_MATCH")
    assert ambiguous is not None
    assert ambiguous.recommendation_id is None


def test_ac_039_recommendations_list_preconditions() -> None:
    src, tgt = _pair(
        [("a", {"identity": {"id": "a"}}), ("b", {"identity": {"id": "b"}})],
        [("a", {"identity": {"id": "a"}})],
    )
    result = localize(src, tgt)
    assert result.recommendations
    assert all(r.preconditions for r in result.recommendations)


def test_ac_040_recommendations_declare_authority() -> None:
    src, tgt = _pair(
        [("a", {"identity": {"id": "a"}}), ("b", {"identity": {"id": "b"}})],
        [("a", {"identity": {"id": "a"}})],
    )
    result = localize(src, tgt, authoritative_side=AuthoritativeSide.SOURCE)
    assert result.recommendations
    assert all(r.authoritative_side is AuthoritativeSide.SOURCE for r in result.recommendations)
