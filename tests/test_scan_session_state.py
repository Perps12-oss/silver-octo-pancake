"""Unit tests for scan session snapshot and UI reducer."""
from cerebro.engines.base_engine import DuplicateFile, DuplicateGroup
from pathlib import Path

from cerebro.v2.ui.scan_session_state import (
    EMPTY_SNAPSHOT,
    compute_dup_count,
    next_snapshot_after_scan,
)
from cerebro.v2.ui.scan_ui_actions import ActionOpenGroup, ActionScanCompleted
from cerebro.v2.ui.scan_ui_reducer import apply_scan_snapshot


def _group(n_files: int, gid: int = 1) -> DuplicateGroup:
    files = [
        DuplicateFile(
            path=Path(f"/x/f{i}.txt"),
            size=10,
            modified=1.0,
            extension=".txt",
        )
        for i in range(n_files)
    ]
    return DuplicateGroup(group_id=gid, files=files)


def test_compute_dup_count() -> None:
    g = [_group(3), _group(1)]
    assert compute_dup_count(g) == 2 + 0


def test_next_snapshot_after_scan_revision_and_mode() -> None:
    s0 = EMPTY_SNAPSHOT
    g = [_group(2)]
    s1 = next_snapshot_after_scan(s0, g, "photos")
    assert s1.revision == 1
    assert s1.mode == "photos"
    assert s1.dup_count == 1
    assert s1.review_tab_enabled is True
    assert len(s1.groups) == 1

    s2 = next_snapshot_after_scan(s1, g, "")
    assert s2.revision == 2
    assert s2.mode == "files"


def test_reducer_only_scan_completed_mutates() -> None:
    s0 = EMPTY_SNAPSHOT
    g = [_group(2)]
    s1 = apply_scan_snapshot(s0, ActionScanCompleted(g, "files"))
    assert s1.revision == 1
    s2 = apply_scan_snapshot(s1, ActionOpenGroup(1, list(g)))
    assert s2 is s1


def test_reducer_normalizes_mode() -> None:
    s = apply_scan_snapshot(EMPTY_SNAPSHOT, ActionScanCompleted([], "  videos  "))
    assert s.mode == "videos"
