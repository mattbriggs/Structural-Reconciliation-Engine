"""Acceptance test AC-036 (profile/version traceability) — implemented portion.

Every result records the exact engine, core-contract, and profile versions
used. Adapter and localization-policy version fields remain a documented
follow-up (the report marks AC-036 PARTIAL).
"""

from __future__ import annotations

import pytest

from tests.app_builders import localize
from tests.builders import TreeBuilder

pytestmark = pytest.mark.acceptance


def test_ac_036_result_records_component_and_profile_versions() -> None:
    src = TreeBuilder("s", "r", node_type="map").child("r", "a", identity={"id": "a"}).build()
    tgt = TreeBuilder("t", "r", node_type="map").child("r", "a", identity={"id": "a"}).build()
    result = localize(src, tgt)
    versions = result.reconciliation.profile_versions
    assert versions.engine_version
    assert versions.core_contract_version
    assert versions.normalization_profile_version
    assert versions.matching_profile_version
    assert versions.alignment_profile_version
    assert versions.operation_profile_version
    assert versions.suppression_profile_version
    # The localization result also carries its own contract version.
    assert result.contract_version == "localization-result-v1"
