"""Longest-common-subsequence alignment over matched keys (REQ-055).

Operates on abstract, hashable keys rather than nodes so it is trivially unit
testable and reusable by the aligner. Returns an ordered edit script of
aligned / left-only / right-only positions. Deterministic for identical input.
"""

from __future__ import annotations

from enum import Enum


class Op(str, Enum):
    """Alignment operation for one position."""

    ALIGN = "ALIGN"
    LEFT_ONLY = "LEFT_ONLY"
    RIGHT_ONLY = "RIGHT_ONLY"


def align_sequences[T](left: list[T], right: list[T]) -> list[tuple[Op, T | None, T | None]]:
    """Align two sequences by longest common subsequence of equal keys.

    :param left: Left (e.g. source) sequence of hashable keys.
    :param right: Right (e.g. target) sequence of hashable keys.
    :returns: Ordered list of ``(op, left_item, right_item)`` triples. For
        ``ALIGN`` both items are set; for ``LEFT_ONLY``/``RIGHT_ONLY`` the
        other side is ``None``.
    """
    n, m = len(left), len(right)
    # dp[i][j] = LCS length of left[i:], right[j:]
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            if left[i] == right[j]:
                dp[i][j] = dp[i + 1][j + 1] + 1
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j + 1])

    script: list[tuple[Op, T | None, T | None]] = []
    i = j = 0
    while i < n and j < m:
        if left[i] == right[j]:
            script.append((Op.ALIGN, left[i], right[j]))
            i += 1
            j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            script.append((Op.LEFT_ONLY, left[i], None))
            i += 1
        else:
            script.append((Op.RIGHT_ONLY, None, right[j]))
            j += 1
    while i < n:
        script.append((Op.LEFT_ONLY, left[i], None))
        i += 1
    while j < m:
        script.append((Op.RIGHT_ONLY, None, right[j]))
        j += 1
    return script
