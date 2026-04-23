"""Single source of truth for post-scan session data (groups, mode, counts).

Pages still hold their own display state; the shell reads scan facts from
``ScanSessionSnapshot`` so orchestration does not fork parallel copies.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Tuple


def compute_dup_count(groups: Iterable[Any]) -> int:
    """Count duplicate *files* (all but one keeper per group)."""
    return sum(max(0, len(getattr(g, "files", ()) or ()) - 1) for g in groups)


@dataclass(frozen=True)
class ScanSessionSnapshot:
    """Immutable snapshot after a scan (shallow tuple of group objects)."""

    revision: int
    groups: Tuple[Any, ...]
    mode: str
    dup_count: int
    review_tab_enabled: bool


EMPTY_SNAPSHOT = ScanSessionSnapshot(
    revision=0,
    groups=tuple(),
    mode="files",
    dup_count=0,
    review_tab_enabled=False,
)


def next_snapshot_after_scan(
    prev: ScanSessionSnapshot,
    groups: Any,
    mode: str,
) -> ScanSessionSnapshot:
    """Pure transition: completed scan replaces session content."""
    g = tuple(groups or ())
    mode_n = (mode or "files").strip() or "files"
    return ScanSessionSnapshot(
        revision=prev.revision + 1,
        groups=g,
        mode=mode_n,
        dup_count=compute_dup_count(g),
        review_tab_enabled=True,
    )


__all__ = [
    "EMPTY_SNAPSHOT",
    "ScanSessionSnapshot",
    "compute_dup_count",
    "next_snapshot_after_scan",
]
