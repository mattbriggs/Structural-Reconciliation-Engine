"""Domain adapters that translate external document models into canonical trees.

Adapters are *anti-corruption layers* (REQ-186, REQ-230): they convert XML,
DITA, or CCMS object models into the domain-neutral
:class:`~reconciliation.core.contracts.tree.CanonicalTree` the core consumes.
Adapters depend on core *contracts* but the core never imports adapters — that
boundary is enforced by ``tests/contract/test_core_independence.py`` (AC-031).
"""

from __future__ import annotations
