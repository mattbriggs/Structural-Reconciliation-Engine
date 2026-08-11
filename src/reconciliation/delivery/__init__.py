"""Delivery layer: CLI and HTTP API composition roots.

Delivery depends on application interfaces and wires concrete adapters,
persistence, and renderers together. It never orchestrates core modules
directly (REQ-247).
"""

from __future__ import annotations
