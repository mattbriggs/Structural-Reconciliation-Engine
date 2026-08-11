"""Tests for the read-only CCMS port, stub adapter, and sourced comparison.

Covers REQ-186 (outside the core), REQ-187 (metadata mapping), REQ-188
(read-only), and REQ-190 (read failure is not a comparison result).
"""

from __future__ import annotations

import pytest

from reconciliation.adapters.ccms.base import map_repository_metadata
from reconciliation.adapters.ccms.stub import StubCCMSReadAdapter
from reconciliation.application.contracts.jobs import ComparisonState
from reconciliation.application.orchestration.ccms_comparison import CCMSComparisonService
from reconciliation.application.orchestration.comparison_job import ComparisonJobService
from reconciliation.application.ports.ccms import (
    CCMSObjectRef,
    CCMSReadError,
    CCMSReadPort,
)
from reconciliation.delivery.composition import build_default_registry

SRC = '<map><topicref keys="intro" href="i.dita"/><topicref keys="gone" href="g.dita"/></map>'
LOC = '<map><topicref keys="intro" href="i.dita"/></map>'


def _adapter() -> StubCCMSReadAdapter:
    adapter = StubCCMSReadAdapter()
    adapter.register("src-1", SRC, revision="3", metadata={"rev": "3", "tuid": "TU-9"})
    adapter.register("loc-1", LOC, revision="2", metadata={"srcRev": "2", "lang": "fr-FR"})
    return adapter


def test_metadata_mapping_neutralizes_keys() -> None:
    mapped = map_repository_metadata({"objectId": "x", "rev": "5", "unknown": "drop"})
    assert mapped == {"object_id": "x", "revision": "5"}
    assert "unknown" not in mapped


def test_stub_returns_registered_object_and_mapped_metadata() -> None:
    adapter = _adapter()
    obj = adapter.get_object(CCMSObjectRef(object_id="src-1"))
    assert obj.content == SRC
    assert obj.metadata == {"revision": "3", "translation_unit_id": "TU-9"}


def test_stub_honors_explicit_revision() -> None:
    adapter = _adapter()
    obj = adapter.get_object(CCMSObjectRef(object_id="loc-1", revision="2"))
    assert obj.revision == "2"


def test_stub_missing_object_raises() -> None:
    adapter = _adapter()
    with pytest.raises(CCMSReadError) as exc:
        adapter.get_object(CCMSObjectRef(object_id="nope"))
    assert exc.value.code == "CCMS_READ_FAILED"


def test_stub_simulated_failure_raises() -> None:
    adapter = _adapter()
    adapter.fail("src-1")
    with pytest.raises(CCMSReadError):
        adapter.get_object(CCMSObjectRef(object_id="src-1"))


def test_ccms_sourced_comparison_completes() -> None:
    service = CCMSComparisonService(
        _adapter(), ComparisonJobService(build_default_registry())
    )
    outcome = service.run_from_refs(
        CCMSObjectRef(object_id="src-1"),
        CCMSObjectRef(object_id="loc-1"),
        locale="fr-FR",
        document_profile_id="dita-map-v1",
        job_id="ccms-1",
    )
    assert outcome.record.state is ComparisonState.COMPLETED
    assert outcome.result is not None
    assert outcome.record.status_counts["MISSING_IN_LOCALE"] == 1


def test_ccms_read_failure_is_not_a_comparison_result() -> None:
    # REQ-190: a CCMS failure yields a rejected job, not a structural result.
    adapter = _adapter()
    adapter.fail("loc-1")
    service = CCMSComparisonService(
        adapter, ComparisonJobService(build_default_registry())
    )
    outcome = service.run_from_refs(
        CCMSObjectRef(object_id="src-1"),
        CCMSObjectRef(object_id="loc-1"),
        locale="fr-FR",
        document_profile_id="dita-map-v1",
    )
    assert outcome.record.state is ComparisonState.REJECTED
    assert outcome.record.error_code == "CCMS_READ_FAILED"
    assert outcome.result is None


def test_stub_satisfies_read_port() -> None:
    adapter: CCMSReadPort = _adapter()
    assert hasattr(adapter, "get_object")
