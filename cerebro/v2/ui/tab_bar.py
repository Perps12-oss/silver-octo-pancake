"""
TabBar — 36 px light tab strip with 6 named tabs.

Active:   white bg, bold text, 3 px #E74C3C underline.
Inactive: #F0F0F0 bg, gray text.
Disabled: #F0F0F0 bg, #BBBBBB text, not clickable.
Badge:    small red pill on the Results tab showing duplicate count.
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable, Dict, List, Optional, Tuple

_SURFACE     = "#F0F0F0"
_WHITE       = "#FFFFFF"
_BORDER      = "#E0E0E0"
_ACTIVE_FG   = "#111111"
_INACTIVE_FG = "#666666"
_DISABLED_FG = "#BBBBBB"
_ACCENT      = "#E74C3C"
_BADGE_BG    = "#E74C3C"

TABS: List[Tuple[str, str]] = [
    ("welcome",     "Welcome"),
    ("scan",        "Scan"),
    ("results",     "Results"),
    ("review",      "Review"),
    ("history",     "History"),
    ("diagnostics", "Diagnostics"),
]


class _Tab(tk.Frame):
    _INDICATOR_H = 3

    def __init__(
        self,
        master,
        key: str,
        label: str,
        on_click: Callable[[str], None],
        **kwargs,
    ) -> None:
        kwargs.setdefault("bg", _SURFACE)
        super().__init__(master, cursor="hand2", **kwargs)
        self._key      = key
        self._on_click = on_click
        self._active   = False
        self._disabled = False

        # Inner frame holds label + optional badge side-by-side
        self._inner = tk.Frame(self, bg=_SURFACE)
        self._inner.pack(fill="both", expand=True, padx=12)

        self._lbl = tk.Label(
            self._inner,
            text=label,
            bg=_SURFACE,
            fg=_INACTIVE_FG,
            font=("Segoe UI", 10),
        )
        self._lbl.pack(side="left", fill="y")

        # Badge — hidden until count > 0
        self._badge_text = tk.StringVar(value="")
        self._badge = tk.Label(
            self._inner,
            textvariable=self._badge_text,
            bg=_BADGE_BG,
            fg="#FFFFFF",
            font=("Segoe UI", 8, "bold"),
            padx=4,
            pady=0,
        )

        # 3 px bottom indicator
        self._indicator = tk.Frame(self, height=self._INDICATOR_H, bg=_SURFACE)
        self._indicator.pack(side="bottom", fill="x")

        for w in (self, self._inner, self._lbl):
            w.bind("<Button-1>", self._click)
            w.bind("<Enter>",    self._hover_in)
            w.bind("<Leave>",    self._hover_out)

    def _click(self, _e=None) -> None:
        if not self._disabled:
            self._on_click(self._key)

    def _hover_in(self, _e=None) -> None:
        if not self._active and not self._disabled:
            self._lbl.configure(fg=_ACTIVE_FG)

    def _hover_out(self, _e=None) -> None:
        if not self._active and not self._disabled:
            self._lbl.configure(fg=_INACTIVE_FG)

    def set_active(self, active: bool) -> None:
        self._active = active
        if active:
            bg = _WHITE
            self.configure(bg=bg)
            self._inner.configure(bg=bg)
            self._lbl.configure(bg=bg, fg=_ACTIVE_FG, font=("Segoe UI", 10, "bold"))
            self._indicator.configure(bg=_ACCENT)
        else:
            bg = _SURFACE
            self.configure(bg=bg)
            self._inner.configure(bg=bg)
            self._lbl.configure(
                bg=bg,
                fg=_DISABLED_FG if self._disabled else _INACTIVE_FG,
                font=("Segoe UI", 10),
            )
            self._indicator.configure(bg=bg)

    def set_disabled(self, disabled: bool) -> None:
        self._disabled = disabled
        self.configure(cursor="" if disabled else "hand2")
        if not self._active:
            self._lbl.configure(fg=_DISABLED_FG if disabled else _INACTIVE_FG)

    def set_badge(self, count: int) -> None:
        if count > 0:
            self._badge_text.set(f" {count} ")
            self._badge.pack(side="left", padx=(4, 0))
        else:
            self._badge_text.set("")
            self._badge.pack_forget()


class TabBar(tk.Frame):
    HEIGHT = 36

    def __init__(
        self,
        master,
        on_tab_changed: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        kwargs.setdefault("bg", _SURFACE)
        kwargs.setdefault("height", self.HEIGHT)
        super().__init__(master, **kwargs)
        self.pack_propagate(False)

        self._on_tab_changed = on_tab_changed
        self._tabs: Dict[str, _Tab] = {}
        self._active_key: str = "welcome"

        self._build()
        # Bottom border drawn as a child frame
        tk.Frame(self, bg=_BORDER, height=1).pack(side="bottom", fill="x")

    def _build(self) -> None:
        inner = tk.Frame(self, bg=_SURFACE)
        inner.pack(side="left", fill="y")
        for key, label in TABS:
            tab = _Tab(inner, key=key, label=label, on_click=self._tab_clicked)
            tab.pack(side="left", fill="y")
            self._tabs[key] = tab
        self._tabs["welcome"].set_active(True)
        self._tabs["review"].set_disabled(True)

    def _tab_clicked(self, key: str) -> None:
        if key == self._active_key:
            return
        self._tabs[self._active_key].set_active(False)
        self._active_key = key
        self._tabs[key].set_active(True)
        if self._on_tab_changed:
            self._on_tab_changed(key)

    # ------------------------------------------------------------------
    # Public API

    def switch_to(self, key: str) -> None:
        self._tab_clicked(key)

    def get_active(self) -> str:
        return self._active_key

    def on_tab_changed(self, cb: Callable[[str], None]) -> None:
        self._on_tab_changed = cb

    def set_results_badge(self, count: int) -> None:
        self._tabs["results"].set_badge(count)

    def enable_review(self) -> None:
        self._tabs["review"].set_disabled(False)

    def disable_review(self) -> None:
        self._tabs["review"].set_disabled(True)
