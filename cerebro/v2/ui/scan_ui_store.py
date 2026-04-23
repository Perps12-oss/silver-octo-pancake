"""Dispatch + reducer + effect routing for scan-related shell actions."""
from __future__ import annotations

import tkinter as tk
from typing import Callable

from cerebro.v2.ui.scan_completion import ScanCompletionCoordinator
from cerebro.v2.ui.scan_session_state import ScanSessionSnapshot, EMPTY_SNAPSHOT
from cerebro.v2.ui.scan_ui_actions import (
    ActionNavigateResults,
    ActionOpenGroup,
    ActionOpenSession,
    ActionScanCompleted,
    ActionScanHistoryCleared,
    ScanUiAction,
)
from cerebro.v2.ui.scan_ui_reducer import apply_scan_snapshot


class ScanUiStore:
    """Owns ``ScanSessionSnapshot``; ``dispatch`` runs reducer then effects."""

    def __init__(
        self,
        *,
        coordinator: ScanCompletionCoordinator,
        review_page: object,
        welcome_refresh: Callable[[], None],
        history_refresh: Callable[[], None],
        switch_tab: Callable[[str], None],
    ) -> None:
        self._snapshot: ScanSessionSnapshot = EMPTY_SNAPSHOT
        self._coordinator = coordinator
        self._review_page = review_page
        self._welcome_refresh = welcome_refresh
        self._history_refresh = history_refresh
        self._switch_tab = switch_tab

    @property
    def scan_snapshot(self) -> ScanSessionSnapshot:
        return self._snapshot

    def dispatch(self, action: ScanUiAction) -> None:
        self._snapshot = apply_scan_snapshot(self._snapshot, action)
        if isinstance(action, ActionScanCompleted):
            self._coordinator.run_after_scan(self._snapshot)
        elif isinstance(action, ActionOpenGroup):
            mode = self._snapshot.mode
            self._review_page.load_group(action.groups, action.group_id, mode=mode)
            self._switch_tab("review")
        elif isinstance(action, ActionScanHistoryCleared):
            try:
                self._welcome_refresh()
            except (AttributeError, tk.TclError):
                pass
            try:
                self._history_refresh()
            except (AttributeError, tk.TclError):
                pass
        elif isinstance(action, ActionOpenSession):
            _ = action.session
            self._switch_tab("results")
        elif isinstance(action, ActionNavigateResults):
            self._switch_tab("results")


__all__ = ["ScanUiStore"]
