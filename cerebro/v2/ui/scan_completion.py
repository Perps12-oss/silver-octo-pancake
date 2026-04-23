"""Orchestrates UI effects after a scan completes (kept out of AppShell)."""
from __future__ import annotations

import logging
import tkinter as tk
from typing import Callable, List

from cerebro.v2.ui.scan_session_state import ScanSessionSnapshot

_log = logging.getLogger(__name__)


class ScanCompletionCoordinator:
    """Ordered procedure: load pages, chrome, then navigate."""

    def __init__(
        self,
        *,
        results_page: object,
        review_page: object,
        welcome_refresh: Callable[[], None],
        set_results_badge: Callable[[int], None],
        enable_review_tab: Callable[[], None],
        switch_tab: Callable[[str], None],
    ) -> None:
        self._results_page = results_page
        self._review_page = review_page
        self._welcome_refresh = welcome_refresh
        self._set_results_badge = set_results_badge
        self._enable_review_tab = enable_review_tab
        self._switch_tab = switch_tab

    def run_after_scan(self, snapshot: ScanSessionSnapshot) -> None:
        """Drive Results + Review from the canonical snapshot (single source)."""
        groups: List = list(snapshot.groups)
        mode = snapshot.mode
        self._results_page.load_results(groups, mode=mode)
        try:
            self._review_page.load_results(groups, mode=mode)
        except Exception:  # pylint: disable=broad-except
            _log.exception("ReviewPage.load_results failed")
        self._set_results_badge(snapshot.dup_count)
        self._enable_review_tab()
        try:
            self._welcome_refresh()
        except (AttributeError, tk.TclError):
            pass
        self._switch_tab("results")


__all__ = ["ScanCompletionCoordinator"]
