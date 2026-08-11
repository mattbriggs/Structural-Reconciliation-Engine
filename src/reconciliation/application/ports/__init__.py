"""Application ports (Protocols) implemented by infrastructure adapters.

Ports invert the dependency so storage, artifacts, and integrations are
replaceable (Ports & Adapters, REQ-227, REQ-250). Application code depends on
these Protocols; infrastructure provides implementations. Tests exercise the
application against in-memory fakes.
"""

from __future__ import annotations
