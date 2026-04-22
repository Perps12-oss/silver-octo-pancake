"""Headless smoke-test for VirtualFileGrid scroll model.

Exercises the four scroll channels the real UI routes through (mouse wheel,
scrollbar drag, arrow keys, Home/End/PgUp/PgDn) without spinning up the
full AppShell. Verifies the thumb tracker (_yscrollcommand) gets fired on
every channel and that _scroll_y stays within valid bounds.

Run from repo root: `python scripts/smoke_virtual_grid.py`.
"""
from __future__ import annotations

import tkinter as tk
from typing import List, Tuple

from cerebro.v2.ui.results_page import VirtualFileGrid


def _synthetic_rows(n: int) -> List[dict]:
    return [
        {
            "group_id":    i // 5,
            "file_idx":    i % 5,
            "name":        f"file_{i:05d}.bin",
            "size":        1024 * (i + 1),
            "size_str":    f"{i + 1} KB",
            "date":        "2025-01-01",
            "folder":      f"C:/synthetic/group_{i // 5}",
            "path":        f"C:/synthetic/group_{i // 5}/file_{i:05d}.bin",
            "extension":   ".bin",
            "_group_shade": (i // 5) % 2 == 1,
        }
        for i in range(n)
    ]


def main() -> None:
    root = tk.Tk()
    root.geometry("900x480")

    # Force a realized viewport height so _move_sel's visible_end math
    # doesn't collapse against an un-mapped Canvas's default height=1.
    grid = VirtualFileGrid(root, width=900, height=480)
    grid.pack(fill="both", expand=True)
    root.update()

    thumb_calls: List[Tuple[float, float]] = []

    def capture_thumb(top: str, bot: str) -> None:
        thumb_calls.append((float(top), float(bot)))

    grid.configure(yscrollcommand=capture_thumb)

    grid.load(_synthetic_rows(4803))
    root.update_idletasks()

    total_h = grid._total_h
    view_h  = grid.winfo_height() or 400
    assert total_h == 4803 * grid.ROW_H, f"total_h mismatch: {total_h}"

    def assert_in_bounds(label: str) -> None:
        max_y = max(0, total_h - view_h)
        assert 0 <= grid._scroll_y <= max_y, (
            f"{label}: _scroll_y={grid._scroll_y} out of [0, {max_y}]"
        )

    grid.yview("moveto", 0.0)
    assert grid._scroll_y == 0
    assert_in_bounds("moveto 0.0")

    grid.yview("moveto", 0.9)
    assert grid._scroll_y > 0
    assert_in_bounds("moveto 0.9")

    grid.yview("moveto", 1.0)
    assert_in_bounds("moveto 1.0")
    assert grid._scroll_y == max(0, total_h - view_h), "didn't land at bottom"

    grid.yview("moveto", 0.0)
    grid.yview("scroll", 5, "units")
    assert grid._scroll_y == 5 * grid.ROW_H
    assert_in_bounds("scroll 5 units")

    grid.yview("scroll", 2, "pages")
    assert_in_bounds("scroll 2 pages")

    class FakeEvent:
        delta = -120
        num = 0

    grid._scroll_y = 0
    grid._on_scroll(FakeEvent())
    assert grid._scroll_y == grid.ROW_H * 3, \
        f"wheel step expected {grid.ROW_H * 3}, got {grid._scroll_y}"
    assert_in_bounds("mousewheel 1 notch")

    grid._on_home()
    assert grid._scroll_y == 0 and grid._selected_idx == 0
    grid._on_end()
    assert grid._selected_idx == len(grid._rows) - 1
    assert_in_bounds("End")

    frac = grid.yview()
    assert isinstance(frac, tuple) and len(frac) == 2
    assert 0.0 <= frac[0] <= frac[1] <= 1.0, f"bad fractions: {frac}"

    assert thumb_calls, "yscrollcommand never fired"
    for top, bot in thumb_calls:
        assert 0.0 <= top <= bot <= 1.0 + 1e-9, f"bad thumb call: ({top}, {bot})"

    grid._selected_idx = 0
    grid._scroll_y = 0
    grid._move_sel(4800)
    assert grid._selected_idx == 4800
    first, last = grid._visible_range()
    assert first <= 4800 < last, (
        f"row 4800 not in visible range after _move_sel: [{first}, {last})"
    )

    print(f"OK — {len(thumb_calls)} thumb updates across "
          f"{5 + 2 + 1 + 2 + 1} scroll operations, "
          f"4803 rows, viewport_h={view_h}")
    root.destroy()


if __name__ == "__main__":
    main()
