"""DITA map document adapter (anti-corruption layer, REQ-033).

Maps DITA map vocabulary (``topicref``, ``keydef``, ``topichead``, ``mapref``,
``topicmeta``/``navtitle``, ``@href``, ``@keys``, ``xml:id``) onto canonical
identity, content, and structural properties without leaking DITA element
names into the core (REQ-249). The scope is elements, attributes, references,
and metadata — not full DITA key/conref graph expansion (an open question,
SRS §10).
"""

from __future__ import annotations
