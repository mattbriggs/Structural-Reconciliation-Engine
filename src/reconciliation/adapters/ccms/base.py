"""CCMS anti-corruption helpers (REQ-187).

Maps CCMS-specific repository metadata keys onto a neutral, stable vocabulary
so downstream layers never depend on a particular CCMS's field names. The
mapping is intentionally small and explicit; production adapters extend it for
their repository.
"""

from __future__ import annotations

#: Default mapping from common CCMS metadata keys to neutral keys. Production
#: adapters override/extend this for their specific repository.
DEFAULT_METADATA_MAP: dict[str, str] = {
    "objectId": "object_id",
    "object_id": "object_id",
    "rev": "revision",
    "revision": "revision",
    "srcRev": "source-revision",
    "source_revision": "source-revision",
    "tuid": "translation_unit_id",
    "translationUnitId": "translation_unit_id",
    "locale": "locale",
    "lang": "locale",
}


def map_repository_metadata(
    raw: dict[str, str], mapping: dict[str, str] | None = None
) -> dict[str, str]:
    """Translate repository metadata into the neutral vocabulary (REQ-187).

    :param raw: CCMS-specific metadata.
    :param mapping: Optional override of the default key mapping.
    :returns: Metadata keyed by neutral names; unknown keys are dropped so no
        CCMS-specific field leaks downstream.
    """
    table = mapping or DEFAULT_METADATA_MAP
    result: dict[str, str] = {}
    for key, value in raw.items():
        neutral = table.get(key)
        if neutral is not None:
            result[neutral] = value
    return result
