"""
ThemeApplicator — applies the active theme to all shell pages.

Every page registers its themed widgets here. When the theme changes,
ThemeApplicator.apply(theme_name) reconfigures all registered widgets
in a single pass via after_idle() to avoid blocking.
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable, List


def _tc(slot: str) -> str:
    """Read a color slot from the active theme."""
    from cerebro.v2.core.theme_bridge_v2 import theme_color
    return theme_color(slot)


class ThemeApplicator:
    """Singleton theme applicator for the new shell."""

    _instance: "ThemeApplicator | None" = None

    @classmethod
    def get(cls) -> "ThemeApplicator":
        if cls._instance is None:
            cls._instance = ThemeApplicator()
        return cls._instance

    def __init__(self) -> None:
        self._hooks: List[Callable[[dict], None]] = []
        self._current: str = "Cerebro Dark"

    def register(self, hook: Callable[[dict], None]) -> None:
        """Register a callback that receives the full theme token dict."""
        self._hooks.append(hook)

    def apply(self, theme_name: str, root: tk.Misc) -> None:
        """Switch to a new theme and notify all registered pages."""
        try:
            from cerebro.core.theme_engine_v3 import ThemeEngineV3
            ThemeEngineV3.get().set_theme(theme_name)
            self._current = theme_name
        except Exception:
            pass
        tokens = self.build_tokens()
        root.after_idle(lambda: self._dispatch(tokens))

    def build_tokens(self) -> dict:
        """Build a flat token dict from the currently active theme."""
        return {
            # Base
            "bg":              _tc("base.background"),
            "bg2":             _tc("base.backgroundSecondary"),
            "bg3":             _tc("base.backgroundTertiary"),
            "fg":              _tc("base.foreground"),
            "fg2":             _tc("base.foregroundSecondary"),
            "fg_muted":        _tc("base.foregroundMuted"),
            "border":          _tc("base.border"),
            # Shell
            "title_bar_bg":    _tc("shell.titleBarBackground"),
            "accent":          _tc("shell.accentPrimary"),
            "accent2":         _tc("shell.accentSecondary"),
            "danger":          _tc("shell.accentDanger"),
            "success":         _tc("shell.accentSuccess"),
            "nav_bar":         _tc("shell.navyBar"),
            "row_alt":         _tc("shell.rowAlt"),
            "row_sel":         _tc("shell.rowSelected"),
            "row_sel_fg":      _tc("shell.rowSelectedText"),
            "tree_sel":        _tc("shell.treeSelected"),
            "stat_dupes":      _tc("shell.statDuplicates"),
            "stat_space":      _tc("shell.statSpace"),
            # Tabs
            "tab_bg":          _tc("tabs.background"),
            "tab_active_bg":   _tc("tabs.activeBackground"),
            "tab_active_fg":   _tc("tabs.activeForeground"),
            "tab_indicator":   _tc("tabs.activeBorder"),
            "tab_inactive_bg": _tc("tabs.inactiveBackground"),
            "tab_inactive_fg": _tc("tabs.inactiveForeground"),
            "tab_hover_bg":    _tc("tabs.inactiveBackgroundHover"),
            # Theme name for reference
            "_name":           self._current,
        }

    def _dispatch(self, tokens: dict) -> None:
        for hook in self._hooks:
            try:
                hook(tokens)
            except Exception as e:
                print(f"[ThemeApplicator] hook error: {e}")


__all__ = ["ThemeApplicator"]
