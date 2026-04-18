"""
ResultsPage — post-scan results with canvas-based virtual file grid.

Stats bar · Action toolbar · Filter tabs · VirtualFileGrid
"""
from __future__ import annotations

import os
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Any, Callable, Dict, List, Optional, Set

try:
    import customtkinter as ctk
    CTkFrame    = ctk.CTkFrame
    CTkLabel    = ctk.CTkLabel
    CTkButton   = ctk.CTkButton
    CTkToplevel = ctk.CTkToplevel
except ImportError:
    CTkFrame    = tk.Frame      # type: ignore[misc,assignment]
    CTkLabel    = tk.Label      # type: ignore[misc,assignment]
    CTkButton   = tk.Button     # type: ignore[misc,assignment]
    CTkToplevel = tk.Toplevel   # type: ignore[misc,assignment]

from cerebro.engines.base_engine import DuplicateGroup, DuplicateFile

# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------
_WHITE    = "#FFFFFF"
_SURFACE  = "#F0F0F0"
_ROW_ALT  = "#F8F8F8"
_SELECTED = "#1E3A8A"
_SEL_FG   = "#FFFFFF"
_BORDER   = "#E0E0E0"
_BTN_BD   = "#DDDDDD"
_NAVY_MID = "#1E3A5F"
_RED      = "#E74C3C"
_GREEN    = "#27AE60"
_GRAY     = "#666666"
_DIMGRAY  = "#AAAAAA"
_HDR_BG   = "#E8E8E8"

# File-type extension sets for filter tabs
_EXT_MUSIC  = {".mp3",".flac",".ogg",".wav",".aac",".m4a",".wma",".opus",".aiff",".ape"}
_EXT_PIC    = {".jpg",".jpeg",".png",".gif",".bmp",".webp",".heic",".tiff",".tif",
               ".cr2",".cr3",".nef",".arw",".dng"}
_EXT_VID    = {".mp4",".avi",".mkv",".mov",".wmv",".flv",".webm",".m4v",".mpg",".mpeg"}
_EXT_DOC    = {".pdf",".doc",".docx",".xls",".xlsx",".ppt",".pptx",".txt",".odt",".rtf"}
_EXT_ARCH   = {".zip",".rar",".7z",".tar",".gz",".bz2",".xz",".iso"}

_FILTER_EXTS: Dict[str, Optional[Set[str]]] = {
    "all": None,
    "music": _EXT_MUSIC,
    "pictures": _EXT_PIC,
    "videos": _EXT_VID,
    "documents": _EXT_DOC,
    "archives": _EXT_ARCH,
}


def _fmt_size(n: int) -> str:
    if n < 1024:       return f"{n} B"
    if n < 1024**2:    return f"{n/1024:.1f} KB"
    if n < 1024**3:    return f"{n/1024**2:.1f} MB"
    return             f"{n/1024**3:.1f} GB"


def _fmt_date(ts: float) -> str:
    if not ts:
        return "—"
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    except Exception:
        return "—"


# ---------------------------------------------------------------------------
# Columns definition  (name, fixed_width — 0 = flex)
# ---------------------------------------------------------------------------
COLS = [("☐", 28), ("Name", 260), ("Size", 88), ("Date", 110), ("Folder", 0)]


def _col_x_widths(total_w: int):
    """Return list of (name, x_start, width) for all columns."""
    flex_w = max(0, total_w - sum(w for _, w in COLS if w > 0))
    result, x = [], 0
    for name, w in COLS:
        cw = w if w > 0 else flex_w
        result.append((name, x, cw))
        x += cw
    return result


# ===========================================================================
# VirtualFileGrid
# ===========================================================================

class VirtualFileGrid(tk.Canvas):
    """Canvas-based virtual file list — smooth at 5 000+ rows."""

    ROW_H = 24

    def __init__(self, parent, on_open_group: Optional[Callable[[int], None]] = None,
                 **kw) -> None:
        kw.setdefault("bg", _WHITE)
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, **kw)
        self._rows:         List[Dict]     = []
        self._checked:      Set[int]       = set()       # row indices
        self._selected_idx: Optional[int]  = None
        self._scroll_y:     int            = 0
        self._sort_col:     str            = "Name"
        self._sort_asc:     bool           = True
        self._on_open_group = on_open_group
        self._total_h:      int            = 0

        self.bind("<MouseWheel>",    self._on_scroll)
        self.bind("<Button-1>",      self._on_click)
        self.bind("<Double-Button-1>", self._on_dbl)
        self.bind("<Configure>",     lambda _e: self._render())
        self.bind("<space>",         self._on_space)
        self.bind("<Up>",            lambda _e: self._move_sel(-1))
        self.bind("<Down>",          lambda _e: self._move_sel(1))
        self.bind("<Return>",        lambda _e: self._open_selected())
        self.bind("<Control-a>",     lambda _e: self._check_all())
        self.bind("<Control-A>",     lambda _e: self._check_all())
        self.bind("<Delete>",        lambda _e: self._mark_selected_delete())

    # ------------------------------------------------------------------
    # Data

    def load(self, rows: List[Dict]) -> None:
        self._rows = rows
        self._checked.clear()
        self._selected_idx = None
        self._scroll_y = 0
        self._total_h = len(rows) * self.ROW_H
        self._render()

    def get_checked_rows(self) -> List[Dict]:
        return [self._rows[i] for i in sorted(self._checked) if i < len(self._rows)]

    def get_checked_count(self) -> int:
        return len(self._checked)

    # ------------------------------------------------------------------
    # Rendering

    def _visible_range(self):
        h = self.winfo_height() or 400
        first = max(0, self._scroll_y // self.ROW_H)
        last  = min(len(self._rows), first + h // self.ROW_H + 2)
        return first, last

    def _render(self) -> None:
        self.delete("row")
        if not self._rows:
            self.create_text(self.winfo_width() // 2 or 200, 80,
                             text="No results to display.",
                             fill=_DIMGRAY, font=("Segoe UI", 11), tags="row")
            return

        w = self.winfo_width() or 800
        cols = _col_x_widths(w)
        first, last = self._visible_range()

        for i in range(first, last):
            row  = self._rows[i]
            y    = i * self.ROW_H - self._scroll_y
            is_sel = (i == self._selected_idx)
            is_chk = (i in self._checked)

            # Row background
            if is_sel:
                bg = _SELECTED
            elif row.get("_group_shade"):
                bg = _ROW_ALT
            else:
                bg = _WHITE
            fg = _SEL_FG if is_sel else "#333333"

            self.create_rectangle(0, y, w, y + self.ROW_H,
                                  fill=bg, outline="", tags="row")

            for col_name, cx, cw in cols:
                if cw <= 0:
                    continue
                if col_name == "☐":
                    chk = "☑" if is_chk else "☐"
                    self.create_text(cx + cw // 2, y + self.ROW_H // 2,
                                     text=chk, fill=fg, anchor="center",
                                     font=("Segoe UI", 10), tags="row")
                elif col_name == "Name":
                    name = row.get("name", "")
                    if len(name) > 38:
                        name = name[:36] + "…"
                    self.create_text(cx + 4, y + self.ROW_H // 2,
                                     text=name, fill=fg, anchor="w",
                                     font=("Segoe UI", 10), tags="row")
                elif col_name == "Size":
                    self.create_text(cx + cw - 4, y + self.ROW_H // 2,
                                     text=row.get("size_str", ""),
                                     fill=fg, anchor="e",
                                     font=("Segoe UI", 10), tags="row")
                elif col_name == "Date":
                    self.create_text(cx + 4, y + self.ROW_H // 2,
                                     text=row.get("date", ""),
                                     fill=fg, anchor="w",
                                     font=("Segoe UI", 10), tags="row")
                elif col_name == "Folder":
                    folder = row.get("folder", "")
                    max_chars = max(0, cw // 7)
                    if len(folder) > max_chars:
                        folder = "…" + folder[-(max_chars - 1):]
                    self.create_text(cx + 4, y + self.ROW_H // 2,
                                     text=folder, fill=fg, anchor="w",
                                     font=("Segoe UI", 10), tags="row")

        # Scrollbar region
        self.configure(scrollregion=(0, 0, w, self._total_h))

    # ------------------------------------------------------------------
    # Interaction

    def _on_scroll(self, event) -> None:
        h = self.winfo_height()
        max_scroll = max(0, self._total_h - h)
        self._scroll_y = max(0, min(max_scroll,
                                    self._scroll_y - event.delta // 2))
        self._render()

    def _row_at_y(self, y: int) -> Optional[int]:
        idx = (y + self._scroll_y) // self.ROW_H
        return idx if 0 <= idx < len(self._rows) else None

    def _on_click(self, event) -> None:
        self.focus_set()
        idx = self._row_at_y(event.y)
        if idx is None:
            return
        w = self.winfo_width() or 800
        cols = _col_x_widths(w)
        chk_end = cols[0][1] + cols[0][2]  # end of checkbox column
        if event.x <= chk_end:
            if idx in self._checked:
                self._checked.discard(idx)
            else:
                self._checked.add(idx)
        else:
            self._selected_idx = idx
        self._render()
        self._fire_check_change()

    def _on_dbl(self, event) -> None:
        idx = self._row_at_y(event.y)
        if idx is not None:
            self._selected_idx = idx
            self._open_selected()

    def _open_selected(self) -> None:
        if self._selected_idx is not None and self._on_open_group:
            row = self._rows[self._selected_idx]
            self._on_open_group(row.get("group_id", 0))

    def _on_space(self, _event) -> None:
        if self._selected_idx is not None:
            if self._selected_idx in self._checked:
                self._checked.discard(self._selected_idx)
            else:
                self._checked.add(self._selected_idx)
            self._render()
            self._fire_check_change()

    def _move_sel(self, delta: int) -> None:
        if not self._rows:
            return
        cur = self._selected_idx or 0
        nxt = max(0, min(len(self._rows) - 1, cur + delta))
        self._selected_idx = nxt
        # Auto-scroll
        visible_start = self._scroll_y // self.ROW_H
        visible_end   = visible_start + self.winfo_height() // self.ROW_H - 1
        if nxt < visible_start:
            self._scroll_y = nxt * self.ROW_H
        elif nxt > visible_end:
            self._scroll_y = (nxt - visible_end + visible_start) * self.ROW_H
        self._render()

    def _check_all(self) -> None:
        if len(self._checked) == len(self._rows):
            self._checked.clear()
        else:
            self._checked = set(range(len(self._rows)))
        self._render()
        self._fire_check_change()

    def _mark_selected_delete(self) -> None:
        if self._selected_idx is not None:
            self._checked.add(self._selected_idx)
            self._render()
            self._fire_check_change()

    def _fire_check_change(self) -> None:
        self.event_generate("<<CheckChanged>>")

    # ------------------------------------------------------------------
    # Sorting

    def sort_by(self, col: str) -> None:
        if col == self._sort_col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col
            self._sort_asc = True
        key_map = {
            "Name": lambda r: r.get("name", "").lower(),
            "Size": lambda r: r.get("size", 0),
            "Date": lambda r: r.get("date", ""),
            "Folder": lambda r: r.get("folder", "").lower(),
        }
        key = key_map.get(col, lambda r: r.get("name", ""))
        self._rows.sort(key=key, reverse=not self._sort_asc)
        self._checked.clear()
        self._selected_idx = None
        self._render()
        self._fire_check_change()


# ===========================================================================
# Column header
# ===========================================================================

class _ColHeader(tk.Canvas):
    H = 28

    def __init__(self, parent, on_sort: Callable[[str], None], **kw) -> None:
        kw.setdefault("bg", _HDR_BG)
        kw.setdefault("height", self.H)
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, **kw)
        self._on_sort   = on_sort
        self._sort_col  = "Name"
        self._sort_asc  = True
        self.bind("<Configure>", lambda _e: self._render())
        self.bind("<Button-1>",  self._on_click)

    def _render(self) -> None:
        self.delete("all")
        w = self.winfo_width() or 800
        cols = _col_x_widths(w)
        for col_name, cx, cw in cols:
            if cw <= 0:
                continue
            label = col_name
            if col_name == self._sort_col and col_name not in ("☐",):
                label += " ▲" if self._sort_asc else " ▼"
            self.create_text(cx + 4, self.H // 2, text=label,
                             fill="#555555", anchor="w",
                             font=("Segoe UI", 9, "bold"))
            # column divider
            self.create_line(cx + cw - 1, 4, cx + cw - 1, self.H - 4,
                             fill=_BORDER)

    def _on_click(self, event) -> None:
        w = self.winfo_width() or 800
        cols = _col_x_widths(w)
        for col_name, cx, cw in cols:
            if col_name in ("☐",):
                continue
            if cx <= event.x < cx + cw:
                self._sort_col = col_name
                self._sort_asc = not self._sort_asc if col_name == self._sort_col else True
                self._render()
                self._on_sort(col_name)
                break

    def set_sort(self, col: str, asc: bool) -> None:
        self._sort_col = col
        self._sort_asc = asc
        self._render()


# ===========================================================================
# Stats bar
# ===========================================================================

class _StatsBar(tk.Frame):
    H = 48

    def __init__(self, master, **kw) -> None:
        kw.setdefault("bg", _WHITE)
        kw.setdefault("height", self.H)
        super().__init__(master, **kw)
        self.pack_propagate(False)
        self._build()

    def _build(self) -> None:
        tk.Frame(self, bg=_BORDER, height=1).pack(side="bottom", fill="x")
        inner = tk.Frame(self, bg=_WHITE)
        inner.pack(fill="both", expand=True, padx=16)

        # Pie chart placeholder (24×24 canvas)
        pie = tk.Canvas(inner, width=24, height=24,
                        bg=_WHITE, highlightthickness=0)
        pie.pack(side="left", padx=(0, 12))
        self._pie = pie

        # 3 stat groups
        self._labels: Dict[str, tk.Label] = {}
        groups = [
            ("files_scanned",  "#111111", "Files scanned"),
            ("duplicates",     _RED,      "Duplicates found"),
            ("recoverable",    _GREEN,    "Space recoverable"),
        ]
        for i, (key, fg, lbl_text) in enumerate(groups):
            if i:
                tk.Frame(inner, bg=_BORDER, width=1).pack(side="left", fill="y",
                                                           padx=20, pady=8)
            col = tk.Frame(inner, bg=_WHITE)
            col.pack(side="left")
            val_lbl = tk.Label(col, text="0", bg=_WHITE, fg=fg,
                               font=("Segoe UI", 18, "bold"))
            val_lbl.pack()
            tk.Label(col, text=lbl_text, bg=_WHITE, fg=_GRAY,
                     font=("Segoe UI", 9)).pack()
            self._labels[key] = val_lbl

    def update(self, files: int, dupes: int, recoverable: int) -> None:
        self._labels["files_scanned"].configure(text=f"{files:,}")
        self._labels["duplicates"].configure(text=f"{dupes:,}")
        self._labels["recoverable"].configure(text=_fmt_size(recoverable))
        self._draw_pie(files, dupes)

    def _draw_pie(self, files: int, dupes: int) -> None:
        c = self._pie
        c.delete("all")
        c.create_oval(2, 2, 22, 22, fill=_SURFACE, outline=_BORDER)
        if files > 0:
            pct = min(1.0, dupes / files)
            extent = pct * 360
            if extent > 0:
                c.create_arc(2, 2, 22, 22, start=90,
                             extent=-extent, fill=_RED, outline="")


# ===========================================================================
# Action toolbar
# ===========================================================================

class _ActionToolbar(tk.Frame):
    H = 40

    def __init__(self, master,
                 on_delete: Callable,
                 on_move:   Callable,
                 on_auto_mark: Callable[[str], None],
                 **kw) -> None:
        kw.setdefault("bg", _WHITE)
        kw.setdefault("height", self.H)
        super().__init__(master, **kw)
        self.pack_propagate(False)
        self._on_delete    = on_delete
        self._on_move      = on_move
        self._on_auto_mark = on_auto_mark
        self._has_sel      = False
        self._build()

    def _build(self) -> None:
        tk.Frame(self, bg=_BORDER, height=1).pack(side="bottom", fill="x")
        inner = tk.Frame(self, bg=_WHITE)
        inner.pack(fill="both", expand=True, padx=8)

        def _btn(text, cmd, **extra):
            opts: dict = {
                "text": text,
                "command": cmd,
                "bg": _WHITE,
                "fg": "#333333",
                "font": ("Segoe UI", 10),
                "relief": "flat",
                "cursor": "hand2",
                "padx": 10,
                "pady": 4,
                "highlightbackground": _BTN_BD,
                "highlightthickness": 1,
            }
            opts.update(extra)
            b = tk.Button(inner, **opts)
            b.pack(side="left", padx=3)
            b.bind("<Enter>", lambda _e: b.configure(bg=_SURFACE))
            b.bind("<Leave>", lambda _e: b.configure(bg=_WHITE))
            return b

        self._auto_btn = _btn("Auto Mark ▼", self._show_auto_mark)
        self._del_btn  = _btn("DELETE",      self._on_delete,
                              fg=_RED)
        _btn("MOVE",         self._on_move)
        _btn("COPY",         self._noop)
        _btn("Export results", self._noop)

    def _show_auto_mark(self) -> None:
        opts = [
            ("Mark newer in each group",    "select_except_oldest"),
            ("Mark older in each group",    "select_except_newest"),
            ("Mark all except first",       "select_except_first"),
            ("Mark all except last",        "select_except_last"),
            ("Mark by path contains…",      "select_in_folder"),
        ]
        try:
            win = CTkToplevel(self)
        except Exception:
            win = tk.Toplevel(self)
        win.title("Auto Mark")
        win.resizable(False, False)
        win.geometry("280x220")
        for label, rule in opts:
            tk.Button(win, text=label, bg=_WHITE, fg="#333333",
                      relief="flat", anchor="w", padx=12, pady=6,
                      font=("Segoe UI", 10), cursor="hand2",
                      command=lambda r=rule, w=win: (self._on_auto_mark(r), w.destroy())
                      ).pack(fill="x")

    def set_has_selection(self, has: bool) -> None:
        self._has_sel = has
        self._del_btn.configure(
            highlightbackground=_RED if has else _BTN_BD,
            highlightthickness=2 if has else 1,
        )

    def _noop(self) -> None:
        pass


# ===========================================================================
# Filter tab bar
# ===========================================================================

class _FilterTabBar(tk.Frame):
    H = 32
    TABS = [("all","All"), ("music","Music"), ("pictures","Pictures"),
            ("videos","Videos"), ("documents","Documents"), ("archives","Archives")]

    def __init__(self, master, on_filter: Callable[[str], None], **kw) -> None:
        kw.setdefault("bg", _WHITE)
        kw.setdefault("height", self.H)
        super().__init__(master, **kw)
        self.pack_propagate(False)
        self._on_filter   = on_filter
        self._active      = "all"
        self._ftabs: Dict[str, tk.Label] = {}
        self._build()

    def _build(self) -> None:
        tk.Frame(self, bg=_BORDER, height=1).pack(side="bottom", fill="x")
        left = tk.Frame(self, bg=_WHITE)
        left.pack(side="left", fill="y")
        for key, lbl in self.TABS:
            w = tk.Label(left, text=lbl, bg=_WHITE, fg=_GRAY,
                         font=("Segoe UI", 10), padx=12, cursor="hand2",
                         relief="flat",
                         highlightbackground=_BTN_BD, highlightthickness=1)
            w.pack(side="left", padx=2, pady=4)
            w.bind("<Button-1>", lambda _e, k=key: self._click(k))
            self._ftabs[key] = w
        self._set_active("all")

    def _click(self, key: str) -> None:
        self._set_active(key)
        self._on_filter(key)

    def _set_active(self, key: str) -> None:
        if self._active in self._ftabs:
            self._ftabs[self._active].configure(
                bg=_WHITE, fg=_GRAY, font=("Segoe UI", 10),
                highlightbackground=_BTN_BD)
        self._active = key
        if key in self._ftabs:
            self._ftabs[key].configure(
                bg=_NAVY_MID, fg=_WHITE, font=("Segoe UI", 10, "bold"),
                highlightbackground=_NAVY_MID)


# ===========================================================================
# ResultsPage
# ===========================================================================

class ResultsPage(tk.Frame):
    """Full results page. Call load_results(groups) after a scan completes."""

    def __init__(self, master,
                 on_open_group: Optional[Callable[[int, List[DuplicateGroup]], None]] = None,
                 **kw) -> None:
        kw.setdefault("bg", _WHITE)
        super().__init__(master, **kw)
        self._on_open_group = on_open_group
        self._groups:   List[DuplicateGroup] = []
        self._all_rows: List[Dict]           = []  # flat, unfiltered
        self._filter    = "all"
        self._build()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        self._stats_bar = _StatsBar(self)
        self._stats_bar.pack(fill="x")

        self._toolbar = _ActionToolbar(
            self,
            on_delete=self._delete_checked,
            on_move=self._move_checked,
            on_auto_mark=self._auto_mark,
        )
        self._toolbar.pack(fill="x")

        self._filter_bar = _FilterTabBar(self, on_filter=self._apply_filter)
        self._filter_bar.pack(fill="x")

        self._col_hdr = _ColHeader(self, on_sort=self._on_sort)
        self._col_hdr.pack(fill="x")

        # Canvas grid + scrollbar
        grid_frame = tk.Frame(self, bg=_WHITE)
        grid_frame.pack(fill="both", expand=True)

        self._grid = VirtualFileGrid(
            grid_frame,
            on_open_group=self._open_group_by_id,
        )
        vsb = ttk.Scrollbar(grid_frame, orient="vertical",
                             command=self._grid.yview)
        self._grid.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._grid.pack(fill="both", expand=True)
        self._grid.bind("<<CheckChanged>>", self._on_check_changed)

        # Empty state
        self._empty_lbl = tk.Label(
            self._grid,
            text="No scan results yet.\nRun a scan from the Scan tab.",
            bg=_WHITE, fg=_DIMGRAY,
            font=("Segoe UI", 11), justify="center",
        )
        self._empty_lbl.place(relx=0.5, rely=0.4, anchor="center")

    # ------------------------------------------------------------------
    # Public API

    def load_results(self, groups: List[DuplicateGroup]) -> None:
        self._groups = groups
        self._empty_lbl.place_forget()
        self._all_rows = self._build_rows(groups)
        self._apply_filter(self._filter)

        total_files = sum(len(g.files) for g in groups)
        dupes       = sum(max(0, len(g.files) - 1) for g in groups)
        recoverable = sum(g.reclaimable for g in groups)
        self._stats_bar.update(total_files, dupes, recoverable)

    def _build_rows(self, groups: List[DuplicateGroup]) -> List[Dict]:
        rows = []
        for shade, g in enumerate(groups):
            for fi, f in enumerate(g.files):
                rows.append({
                    "group_id":    g.group_id,
                    "file_idx":    fi,
                    "name":        Path(f.path).name,
                    "size":        f.size,
                    "size_str":    _fmt_size(f.size),
                    "date":        _fmt_date(f.modified),
                    "folder":      str(Path(f.path).parent),
                    "path":        str(f.path),
                    "extension":   getattr(f, "extension", Path(f.path).suffix.lower()),
                    "_group_shade": shade % 2 == 1,
                })
        return rows

    # ------------------------------------------------------------------
    # Filtering

    def _apply_filter(self, key: str) -> None:
        self._filter = key
        exts = _FILTER_EXTS.get(key)
        if exts is None:
            rows = self._all_rows
        else:
            rows = [r for r in self._all_rows if r.get("extension", "") in exts]
        self._grid.load(rows)

    # ------------------------------------------------------------------
    # Sorting

    def _on_sort(self, col: str) -> None:
        self._grid.sort_by(col)

    # ------------------------------------------------------------------
    # Selection / check

    def _on_check_changed(self, _event=None) -> None:
        has = self._grid.get_checked_count() > 0
        self._toolbar.set_has_selection(has)

    # ------------------------------------------------------------------
    # Actions

    def _auto_mark(self, rule: str) -> None:
        """Apply simple auto-mark rules client-side."""
        if not self._groups:
            return
        rows = self._grid._rows
        group_map: Dict[int, List[int]] = {}
        for idx, row in enumerate(rows):
            gid = row["group_id"]
            group_map.setdefault(gid, []).append(idx)

        new_checked: Set[int] = set()
        for gid, idxs in group_map.items():
            if rule in ("select_except_oldest", "select_except_newest"):
                dated = sorted(idxs, key=lambda i: rows[i].get("date", ""))
                keep = dated[0] if rule == "select_except_oldest" else dated[-1]
                new_checked.update(i for i in idxs if i != keep)
            elif rule == "select_except_first":
                new_checked.update(idxs[1:])
            elif rule == "select_except_last":
                new_checked.update(idxs[:-1])
            else:
                new_checked.update(idxs[1:])

        self._grid._checked = new_checked
        self._grid._render()
        self._grid._fire_check_change()

    def _delete_checked(self) -> None:
        checked = self._grid.get_checked_rows()
        if not checked:
            return
        threading.Thread(
            target=self._delete_worker,
            args=(list(checked),),
            daemon=True,
        ).start()

    def _delete_worker(self, rows: List[Dict]) -> None:
        try:
            from cerebro.core.deletion import DeletionEngine, DeletionPolicy, DeletionRequest
            engine  = DeletionEngine()
            request = DeletionRequest(policy=DeletionPolicy.TRASH,
                                      metadata={"source": "results_page"})
            for row in rows:
                try:
                    engine.delete_one(Path(row["path"]), request)
                except Exception:
                    pass
        except ImportError:
            for row in rows:
                try:
                    import send2trash
                    send2trash.send2trash(row["path"])
                except Exception:
                    pass
        # Reload results minus deleted paths
        deleted = {r["path"] for r in rows}
        self.after(0, lambda: self._remove_paths(deleted))

    def _remove_paths(self, paths: Set[str]) -> None:
        self._grid._rows = [r for r in self._grid._rows if r["path"] not in paths]
        self._all_rows   = [r for r in self._all_rows   if r["path"] not in paths]
        self._grid._checked.clear()
        self._grid._total_h = len(self._grid._rows) * VirtualFileGrid.ROW_H
        self._grid._render()
        self._grid._fire_check_change()

    def _move_checked(self) -> None:
        dest = filedialog.askdirectory(title="Move files to…")
        if not dest:
            return
        checked = self._grid.get_checked_rows()
        if not checked:
            return
        dest_path = Path(dest)
        threading.Thread(
            target=self._move_worker,
            args=(list(checked), dest_path),
            daemon=True,
        ).start()

    def _move_worker(self, rows: List[Dict], dest: Path) -> None:
        import shutil
        moved = set()
        for row in rows:
            src = Path(row["path"])
            try:
                shutil.move(str(src), str(dest / src.name))
                moved.add(row["path"])
            except Exception:
                pass
        self.after(0, lambda: self._remove_paths(moved))

    # ------------------------------------------------------------------
    # Open group in Review

    def _open_group_by_id(self, group_id: int) -> None:
        if self._on_open_group:
            self._on_open_group(group_id, self._groups)

    def get_groups(self) -> List[DuplicateGroup]:
        return self._groups
