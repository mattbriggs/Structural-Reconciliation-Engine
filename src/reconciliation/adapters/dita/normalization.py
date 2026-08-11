"""DITA reference normalization (REQ-033).

Normalizes ``@href`` and ``@keys`` values so that source and locale references
compare on their stable, locale-independent portion. This is deliberately
conservative: it strips a leading ``./`` and separates the fragment, but does
**not** resolve keys, key scopes, or conref targets — those remain open
questions and are out of scope for the initial reference profile (SRS §10 Q9-11).
"""

from __future__ import annotations


def normalize_href(href: str) -> str:
    """Return the normalized target portion of a DITA ``@href``.

    :param href: Raw href attribute value.
    :returns: Href without a leading ``./``; fragment retained since it can
        identify a specific topic within a file.
    """
    value = href.strip()
    while value.startswith("./"):
        value = value[2:]
    return value


def normalize_keys(keys: str) -> tuple[str, ...]:
    """Split a DITA ``@keys`` attribute into its individual, ordered keys.

    :param keys: Space-separated key list.
    :returns: Tuple of non-empty keys in declared order.
    """
    return tuple(k for k in keys.split() if k)
