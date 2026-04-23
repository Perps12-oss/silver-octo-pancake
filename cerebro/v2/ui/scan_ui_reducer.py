"""Pure reducer for scan session snapshot (no Tk, no I/O)."""
from __future__ import annotations

from cerebro.v2.ui.scan_session_state import ScanSessionSnapshot, next_snapshot_after_scan
from cerebro.v2.ui.scan_ui_actions import ActionScanCompleted, ScanUiAction


def apply_scan_snapshot(state: ScanSessionSnapshot, action: ScanUiAction) -> ScanSessionSnapshot:
    """Return the next snapshot; only ``ActionScanCompleted`` mutates session."""
    if isinstance(action, ActionScanCompleted):
        return next_snapshot_after_scan(state, action.groups, action.mode)
    # Open group / history / session: navigation and chrome only — no scan replacement.
    return state


__all__ = ["apply_scan_snapshot"]
