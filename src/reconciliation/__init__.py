"""Structural Reconciliation Engine.

A confidence-aware engine that compares hierarchical semantic trees by
establishing logical node correspondence *before* diagnosing structural
differences. The reusable :mod:`reconciliation.core` package is domain
neutral and depends only on in-memory canonical trees and typed profiles;
localization, adaptation, persistence, reporting, and delivery concerns are
layered above it (see the architecture documentation).

.. note::
   Importing this top-level package must never pull in XML, DITA,
   FastAPI, persistence, reporting, or CCMS dependencies. Those live in
   sub-packages that are imported explicitly by the layers that need them.
"""

from __future__ import annotations

from reconciliation.version import (
    CANONICAL_TREE_CONTRACT_VERSION,
    CORE_CONTRACT_VERSION,
    ENGINE_VERSION,
    LOCALIZATION_RESULT_CONTRACT_VERSION,
    __version__,
)

__all__ = [
    "CANONICAL_TREE_CONTRACT_VERSION",
    "CORE_CONTRACT_VERSION",
    "ENGINE_VERSION",
    "LOCALIZATION_RESULT_CONTRACT_VERSION",
    "__version__",
]
