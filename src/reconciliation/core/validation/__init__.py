"""Explicit, individually-testable validators for core contracts.

Model-level Pydantic validation guarantees local shape. These validators
enforce the *whole-tree* and *whole-profile* invariants that require global
knowledge (REQ-165-170, REQ-280-283) and produce structured results so that
positive and negative cases are mechanically inspectable.
"""

from __future__ import annotations
