"""Unit tests for scan in-progress / complete UI helpers in results_panel."""

from __future__ import annotations

import tkinter as tk

import pytest

from cerebro.engines.base_engine import ScanState


def test_stage_label_mapping_known_stages():
    """Each known stage string maps to a non-empty friendly label."""
    from cerebro.v2.ui.results_panel import _STAGE_LABELS

    for key in (
        "discovering",
        "grouping_by_size",
        "hashing_partial",
        "hashing_full",
        "complete",
    ):
        assert key in _STAGE_LABELS
        assert _STAGE_LABELS[key]


def test_stage_label_mapping_unknown_stage_falls_back():
    """Unknown stages must not crash; they should be displayed title-cased."""
    from cerebro.v2.ui.results_panel import friendly_stage_label

    assert friendly_stage_label("weird_custom_stage") == "Weird Custom Stage"


def test_format_duration_seconds_minutes_hours():
    """format_duration returns the expected forms."""
    from cerebro.v2.ui.results_panel import _format_duration

    assert _format_duration(42) == "42s"
    assert _format_duration(252) == "4m 12s"
    assert _format_duration(3600 + 23 * 60) == "1h 23m"


@pytest.fixture(scope="module")
def tk_root():
    """One Tk per module — avoids intermittent TclError from rapid Tk() churn on Windows."""
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        pytest.skip("no display available")
    yield root
    try:
        root.destroy()
    except tk.TclError:
        pass


def test_scan_in_progress_view_throttles_updates(tk_root, monkeypatch):
    """update_progress called >10x in 100ms must result in <=2 actual refreshes."""
    import cerebro.v2.ui.results_panel as rp

    v = rp._ScanInProgressView(tk_root, on_cancel=lambda: None)
    times = iter([i * 0.001 for i in range(100)])
    monkeypatch.setattr(rp.time, "monotonic", lambda: next(times))

    for _ in range(100):
        v.update_progress(
            stage="discovering",
            files_scanned=1,
            files_total=0,
            elapsed_seconds=0.0,
        )
    assert v._apply_calls <= 2


def test_scan_complete_banner_messages_for_completed_states(tk_root):
    """Banner copy for dupes vs empty scan (single Tk session avoids flaky skips)."""
    from cerebro.v2.ui.results_panel import _ScanCompleteBanner

    host = tk.Frame(tk_root)
    host.pack()
    sf = tk.Frame(host)
    sf.pack(side="top")
    host._status_frame = sf

    b = _ScanCompleteBanner(
        host,
        on_auto_mark=lambda: None,
        on_dismiss=lambda: None,
    )
    b.show(
        final_state=ScanState.COMPLETED,
        groups_found=3,
        duplicates_found=10,
        bytes_reclaimable=1024,
        elapsed_seconds=65.0,
    )
    txt = b._text_label.cget("text") if b._text_label else ""
    assert "Scan complete" in txt
    assert "10" in txt
    assert "3" in txt
    b.hide()

    b.show(
        final_state=ScanState.COMPLETED,
        groups_found=0,
        duplicates_found=0,
        bytes_reclaimable=0,
        elapsed_seconds=12.0,
    )
    txt2 = b._text_label.cget("text") if b._text_label else ""
    assert "No duplicates found" in txt2
    b.hide()
