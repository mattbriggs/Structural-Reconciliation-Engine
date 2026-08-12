"""Unit tests for the profile bundle loader (REQ-228, REQ-280-283)."""

from __future__ import annotations

import pytest

from reconciliation.core.errors import InvalidProfileError
from reconciliation.profiles import load_bundle, load_named_bundle


def test_load_named_dita_bundle() -> None:
    bundle = load_named_bundle("dita_map_v1")
    assert bundle.bundle_id == "dita-map-v1"
    assert bundle.version == "v1"
    assert bundle.matching.match_threshold == 0.6
    # Cross-profile consistency holds.
    bundle.validate_consistency()


def test_load_named_generic_bundles() -> None:
    for name, bundle_id in (
        ("generic_xml_v1", "generic-xml-v1"),
        ("generic_json_v1", "generic-json-v1"),
        ("generic_yaml_v1", "generic-yaml-v1"),
    ):
        bundle = load_named_bundle(name)
        assert bundle.bundle_id == bundle_id
        bundle.validate_consistency()


def test_missing_named_bundle_raises() -> None:
    with pytest.raises(InvalidProfileError):
        load_named_bundle("does_not_exist")


def test_load_bundle_rejects_non_mapping() -> None:
    with pytest.raises(InvalidProfileError):
        load_bundle("- just\n- a\n- list\n")


def test_load_bundle_rejects_bad_schema() -> None:
    bad = """
bundle_id: b
version: v1
normalization: {profile_id: n, version: v1}
matching: {profile_id: m, version: v1, evidence_priority: [], match_threshold: 0.6, probable_threshold: 0.4, ambiguity_margin: 0.05}
alignment: {profile_id: a, version: v1}
operation: {profile_id: o, version: v1}
suppression: {profile_id: s, version: v1}
"""
    # Empty evidence_priority is invalid (MatchingProfile validator).
    with pytest.raises(InvalidProfileError):
        load_bundle(bad)


def test_load_bundle_rejects_invalid_yaml() -> None:
    with pytest.raises(InvalidProfileError):
        load_bundle("bundle_id: [unclosed\n")
