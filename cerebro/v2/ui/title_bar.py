"""
TitleBar — 32 px dark-navy bar.

Left:   decorative macOS-style traffic-light dots (non-functional).
Center: "C E R E B R O" wordmark in white.
Right:  "Themes" and "Settings" text links.
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

_NAVY = "#0B1929"
_LINK = "#7A8FA6"   # white ~30 % blended onto navy background


class TitleBar(tk.Frame):
    HEIGHT = 32

    def __init__(
        self,
        master,
        on_settings: Optional[Callable[[], None]] = None,
        on_themes:   Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> None:
        kwargs.setdefault("bg", _NAVY)
        kwargs.setdefault("height", self.HEIGHT)
        super().__init__(master, **kwargs)
        self.pack_propagate(False)
        self._on_settings = on_settings
        self._on_themes   = on_themes
        self._build()

    # ------------------------------------------------------------------

    def _build(self) -> None:
        # ── Left: traffic lights ──────────────────────────────────────
        left = tk.Frame(self, bg=_NAVY)
        left.pack(side="left", padx=(10, 0), fill="y")
        for color in ("#FF5F57", "#FFBD2E", "#28CA41"):
            c = tk.Canvas(left, width=12, height=12,
                          bg=_NAVY, highlightthickness=0)
            c.pack(side="left", padx=3, pady=10)
            c.create_oval(1, 1, 11, 11, fill=color, outline="")

        # ── Center: wordmark (placed, not packed, so it stays centred) ─
        tk.Label(
            self,
            text="C E R E B R O",
            bg=_NAVY,
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
        ).place(relx=0.5, rely=0.5, anchor="center")

        # ── Right: text links ─────────────────────────────────────────
        right = tk.Frame(self, bg=_NAVY)
        right.pack(side="right", padx=(0, 14), fill="y")

        # packed right-to-left so Settings appears rightmost
        for text, cb_attr in [("Settings", "_on_settings"), ("Themes", "_on_themes")]:
            lbl = tk.Label(
                right, text=text, bg=_NAVY, fg=_LINK,
                font=("Segoe UI", 9), cursor="hand2",
            )
            lbl.pack(side="right", padx=6)
            cb = getattr(self, cb_attr)
            if cb:
                lbl.bind("<Button-1>", lambda _e, c=cb: c())
            lbl.bind("<Enter>", lambda _e, w=lbl: w.configure(fg="#FFFFFF"))
            lbl.bind("<Leave>", lambda _e, w=lbl: w.configure(fg=_LINK))

    # ------------------------------------------------------------------
    # Public API

    def set_settings_callback(self, cb: Callable[[], None]) -> None:
        self._on_settings = cb

    def set_themes_callback(self, cb: Callable[[], None]) -> None:
        self._on_themes = cb
