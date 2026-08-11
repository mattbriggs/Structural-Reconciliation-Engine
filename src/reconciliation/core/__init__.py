"""Reusable, domain-neutral structural reconciliation core.

This package is the architectural keel of the system. It must be importable
and fully testable using only in-memory canonical trees and typed profiles,
with **no** dependency on XML, DITA, localization, FastAPI, persistence,
reporting, CCMS, or pricing code (SRS AC-031, REQ-249).

Treat that boundary as a release test, not merely a packaging convention:
``tests/contract/test_core_independence.py`` asserts that importing
:mod:`reconciliation.core` does not import any forbidden module.
"""

from __future__ import annotations
