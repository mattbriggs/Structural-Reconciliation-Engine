"""Profile bundle contract and YAML loader (REQ-017, REQ-280-283).

A :class:`ProfileBundle` groups the five typed core profiles a comparison job
requires. Bundles are authored as YAML that mirrors the profile models, so
loading is a direct, validated ``model_validate`` — no bespoke mapping code to
drift out of sync. Cross-profile consistency is checked with the core profile
validator (REQ-024, REQ-281).
"""

from __future__ import annotations

import importlib.resources
from typing import Any

import yaml

from reconciliation.core.contracts.base import StrictModel
from reconciliation.core.contracts.profiles import (
    AlignmentProfile,
    MatchingProfile,
    NormalizationProfile,
    OperationProfile,
    SuppressionProfile,
)
from reconciliation.core.errors import InvalidProfileError
from reconciliation.core.validation.profile_validator import validate_profiles


class ProfileBundle(StrictModel):
    """A validated set of profiles for one comparison job.

    :ivar bundle_id: Stable identifier for the bundle.
    :ivar version: Bundle version recorded for traceability (REQ-283).
    :ivar normalization: Normalization profile.
    :ivar matching: Matching profile.
    :ivar alignment: Alignment profile.
    :ivar operation: Operation profile.
    :ivar suppression: Suppression profile.
    """

    bundle_id: str
    version: str
    normalization: NormalizationProfile
    matching: MatchingProfile
    alignment: AlignmentProfile
    operation: OperationProfile
    suppression: SuppressionProfile

    def validate_consistency(self) -> None:
        """Run cross-profile validation, raising on inconsistency (REQ-281)."""
        validate_profiles(self.matching, self.operation, self.suppression).raise_if_invalid()


def load_bundle(data: str | bytes) -> ProfileBundle:
    """Load and validate a profile bundle from YAML text.

    :param data: YAML document mirroring :class:`ProfileBundle`.
    :returns: A validated :class:`ProfileBundle`.
    :raises InvalidProfileError: If the YAML is malformed or inconsistent.
    """
    try:
        parsed: Any = yaml.safe_load(data)
    except yaml.YAMLError as exc:
        raise InvalidProfileError(
            "profile bundle is not valid YAML", context={"detail": str(exc)}
        ) from exc
    if not isinstance(parsed, dict):
        raise InvalidProfileError("profile bundle must be a YAML mapping")
    try:
        bundle = ProfileBundle.model_validate(parsed)
    except Exception as exc:
        raise InvalidProfileError(
            "profile bundle failed schema validation", context={"detail": str(exc)}
        ) from exc
    bundle.validate_consistency()
    return bundle


def load_named_bundle(name: str) -> ProfileBundle:
    """Load a packaged profile bundle by file stem (e.g. ``"dita_map_v1"``).

    :param name: File stem under the ``reconciliation.profiles`` package.
    :returns: A validated :class:`ProfileBundle`.
    :raises InvalidProfileError: If the artifact is missing or invalid.
    """
    resource = importlib.resources.files("reconciliation.profiles").joinpath(f"{name}.yaml")
    if not resource.is_file():
        raise InvalidProfileError(f"profile bundle {name!r} not found")
    return load_bundle(resource.read_text(encoding="utf-8"))
