"""
Mode Tabs Widget

Custom tab row matching Ashisoft's style:
  [📄 Files] [🖼 Photos] [🎬 Videos] [🎵 Music] [📁 Empty Folders] [📊 Large Files]

Tabs share one flat strip (`tabs.background`). The selected mode is shown with accent
text plus a 3 px bottom border (`tabs.activeBorder`); inactive tabs use `tabs.foreground`.
Hover uses `tabs.hoverBackground` without a second “filled button” look.
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Optional, Callable, List, Dict

try:
    import customtkinter as ctk
    CTkFrame = ctk.CTkFrame
    CTkLabel = ctk.CTkLabel
except ImportError:
    CTkFrame = tk.Frame
    CTkLabel = tk.Label

from cerebro.v2.core.design_tokens import Spacing, Typography, Dimensions
from cerebro.v2.core.theme_bridge_v2 import theme_color, subscribe_to_theme


class ScanMode:
    """Available scan modes."""

    FILES         = "files"
    PHOTOS        = "photos"
    VIDEOS        = "videos"
    MUSIC         = "music"
    EMPTY_FOLDERS = "empty_folders"
    LARGE_FILES   = "large_files"

    _META: List[Dict[str, str]] = [
        {"key": FILES,         "icon": "📄", "label": "Files"},
        {"key": PHOTOS,        "icon": "🖼", "label": "Photos"},
        {"key": VIDEOS,        "icon": "🎬", "label": "Videos"},
        {"key": MUSIC,         "icon": "🎵", "label": "Music"},
        {"key": EMPTY_FOLDERS, "icon": "📁", "label": "Empty Folders"},
        {"key": LARGE_FILES,   "icon": "📊", "label": "Large Files"},
    ]

    @classmethod
    def display_name(cls, mode: str) -> str:
        for m in cls._META:
            if m["key"] == mode:
                return m["label"]
        return mode

    @classmethod
    def all_modes(cls) -> List[str]:
        return [m["key"] for m in cls._META]

    @classmethod
    def display_names(cls) -> List[str]:
        return [cls.display_name(k) for k in cls.all_modes()]

    @classmethod
    def meta(cls) -> List[Dict[str, str]]:
        return cls._META


class _Tab(tk.Frame):
    """A single clickable tab with icon + label and a bottom-border indicator."""

    INDICATOR_H = 3  # px of the active underline

    def __init__(self, master, mode_key: str, icon: str, label: str,
                 on_click: Callable[[str], None], **kwargs):
        super().__init__(master, cursor="hand2", **kwargs)
        self._mode_key = mode_key
        self._on_click = on_click
        self._active = False

        # Slightly tighter padding + smaller font so six modes fit on typical widths.
        self._lbl = tk.Label(
            self,
            text=f"{icon}  {label}",
            font=Typography.FONT_SM,
            padx=Spacing.SM,
            pady=Spacing.SM,
            cursor="hand2",
        )
        self._lbl.pack(side="top", fill="x")

        # Coloured bottom indicator bar (3 px tall, hidden by default)
        self._indicator = tk.Frame(self, height=self.INDICATOR_H)
        self._indicator.pack(side="bottom", fill="x")

        for widget in (self, self._lbl, self._indicator):
            widget.bind("<Button-1>", self._handle_click)
            widget.bind("<Enter>",    self._on_enter)
            widget.bind("<Leave>",    self._on_leave)

        self.set_active(False)

    def _handle_click(self, _event=None) -> None:
        self._on_click(self._mode_key)

    def _strip_bg(self) -> str:
        return theme_color("tabs.background")

    def _on_enter(self, _event=None) -> None:
        if not self._active:
            hbg = theme_color("tabs.hoverBackground")
            fg = theme_color("tabs.foreground")
            self.configure(bg=hbg)
            self._lbl.configure(bg=hbg, fg=fg)
            self._indicator.configure(bg=hbg)

    def _on_leave(self, _event=None) -> None:
        if not self._active:
            bg = self._strip_bg()
            fg = theme_color("tabs.foreground")
            self.configure(bg=bg)
            self._lbl.configure(bg=bg, fg=fg)
            self._indicator.configure(bg=bg)

    def set_active(self, active: bool) -> None:
        self._active = active
        strip = self._strip_bg()
        accent = theme_color("tabs.activeBorder")
        if active:
            # One flat strip: no solid accent fill (avoids “patchwork” bar).
            bg = strip
            fg = accent
            ind_color = accent
        else:
            bg = strip
            fg = theme_color("tabs.foreground")
            ind_color = strip

        self.configure(bg=bg)
        self._lbl.configure(bg=bg, fg=fg)
        self._indicator.configure(bg=ind_color)

    def apply_theme(self) -> None:
        self.set_active(self._active)


class ModeTabs(CTkFrame):
    """
    Scan mode tab row.

    Tabs are left-aligned on one background; selection is underline + accent label.

    Public API (unchanged from previous CTkSegmentedButton version):
        set_mode(mode: str)
        get_mode() -> str
        on_mode_changed(callback)
    """

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        subscribe_to_theme(self, self._apply_theme)

        self._current_mode: str = ScanMode.FILES
        self._on_mode_changed: Optional[Callable[[str], None]] = None
        self._tabs: Dict[str, _Tab] = {}

        self._build()
        self._apply_theme()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        self.configure(
            fg_color=theme_color("tabs.background"),
            height=Dimensions.MODE_TABS_HEIGHT,
        )

        inner = tk.Frame(self, bg=theme_color("tabs.background"))
        inner.pack(side="left", fill="both")
        self._inner = inner

        for meta in ScanMode.meta():
            tab = _Tab(
                inner,
                mode_key=meta["key"],
                icon=meta["icon"],
                label=meta["label"],
                on_click=self._on_tab_clicked,
                bg=theme_color("tabs.background"),
            )
            tab.pack(side="left", fill="y")
            self._tabs[meta["key"]] = tab

        # Activate the default tab
        self._tabs[self._current_mode].set_active(True)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_tab_clicked(self, mode_key: str) -> None:
        if mode_key == self._current_mode:
            return
        self._tabs[self._current_mode].set_active(False)
        self._current_mode = mode_key
        self._tabs[self._current_mode].set_active(True)
        if self._on_mode_changed:
            self._on_mode_changed(mode_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_mode(self, mode: str) -> None:
        if mode not in ScanMode.all_modes():
            raise ValueError(f"Invalid scan mode: {mode}")
        if mode == self._current_mode:
            return
        self._tabs[self._current_mode].set_active(False)
        self._current_mode = mode
        self._tabs[self._current_mode].set_active(True)

    def get_mode(self) -> str:
        return self._current_mode

    def get_display_mode(self) -> str:
        return ScanMode.display_name(self._current_mode)

    def on_mode_changed(self, callback: Callable[[str], None]) -> None:
        self._on_mode_changed = callback

    # Stub kept for compatibility
    def disable_mode(self, mode: str) -> None: pass
    def enable_all_modes(self) -> None: pass

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _apply_theme(self) -> None:
        try:
            self.configure(fg_color=theme_color("tabs.background"))
            self._inner.configure(bg=theme_color("tabs.background"))
        except (OSError, ValueError, RuntimeError, AttributeError, TypeError, KeyError, ImportError):
            pass
        for tab in self._tabs.values():
            try:
                tab.apply_theme()
            except (OSError, ValueError, RuntimeError, AttributeError, TypeError, KeyError, ImportError):
                pass


logger = __import__('logging').getLogger(__name__)


class ModeNavPanel(ModeTabs):
    """Blueprint-compatible alias wrapper for Ashisoft mode navigation."""

    def __init__(self, master=None, on_mode_change: Optional[Callable[[str], None]] = None, **kwargs):
        super().__init__(master=master, **kwargs)
        if on_mode_change is not None:
            self.on_mode_changed(on_mode_change)
