"""Versioned, file-based profile artifacts (REQ-228, REQ-282-283).

Profiles are version-controlled YAML artifacts loaded into the typed core
profile contracts. This package is a *consumer* of core contracts; the core
never imports it (enforced by the core-independence test, AC-031).
"""

from __future__ import annotations

from reconciliation.profiles.contracts import ProfileBundle, load_bundle, load_named_bundle

__all__ = ["ProfileBundle", "load_bundle", "load_named_bundle"]
