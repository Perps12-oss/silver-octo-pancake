"""Start Page – Mission Control: dashboard and quick launch aligned with v6 structure."""
from __future__ import annotations

from pathlib import Path

# Re-export for backward compatibility (used by scan_options_panel, pages/__init__)
from cerebro.core.models import StartScanConfig  # noqa: F401

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGridLayout, QScrollArea,
)
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from cerebro.ui.components.modern import PageScaffold, PageHeader, ContentCard
from cerebro.ui.components.modern._tokens import token as theme_token
from cerebro.ui.pages.base_station import BaseStation
from cerebro.ui.state_bus import get_state_bus


class StartPage(BaseStation):
    station_id = "mission"
    station_title = "Home"
    navigate_requested = Signal(str)
    folder_added = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._bus = get_state_bus()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._scaffold = PageScaffold(self, show_sidebar=False, show_sticky_action=False)
        layout.addWidget(self._scaffold)

        self._scaffold.set_header(PageHeader(
            "Mission Control",
            "Dashboard and quick launch. Scan strategy and filters are set in Scan and Settings."
        ))

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)
        content_layout.setContentsMargins(18, 18, 18, 18)

        # Dashboard strip: selected roots, active strategy, filters, recent summary
        dashboard = self._build_dashboard()
        content_layout.addWidget(dashboard)

        # Quick launch cards
        cards_label = QLabel("Quick launch")
        cards_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {theme_token('text')};")
        content_layout.addWidget(cards_label)
        cards = self._build_quick_launch_cards()
        content_layout.addLayout(cards)

        # Optional: Resume last scan
        self._resume_card = self._build_resume_card()
        content_layout.addWidget(self._resume_card)

        content_layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setWidget(content)
        self._scaffold.set_content(scroll)

    def _build_dashboard(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("MissionDashboard")
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)
        layout.setContentsMargins(14, 14, 14, 14)
        text = theme_token("text")
        muted = theme_token("muted")
        opts = self._bus.get_scan_options() or {}
        strategy = str(opts.get("scanner_tier") or opts.get("default_scanner_tier") or "turbo")
        self._strategy_label = QLabel(f"Active scan strategy: {strategy}")
        self._strategy_label.setStyleSheet(f"font-size: 13px; color: {text};")
        layout.addWidget(self._strategy_label)
        self._roots_label = QLabel("Scan roots: Set in Scan page")
        self._roots_label.setStyleSheet(f"font-size: 12px; color: {muted};")
        layout.addWidget(self._roots_label)
        filters_note = QLabel("File filters / exclusions: Settings → Scanning")
        filters_note.setStyleSheet(f"font-size: 11px; color: {muted};")
        layout.addWidget(filters_note)
        self._recent_label = QLabel("Recent scan: Run a scan to see summary")
        self._recent_label.setStyleSheet(f"font-size: 12px; color: {muted};")
        layout.addWidget(self._recent_label)
        self._update_recent_scan_label()
        panel.setStyleSheet(f"""
            QFrame#MissionDashboard {{
                background: {theme_token('panel')};
                border: 1px solid {theme_token('line')};
                border-radius: 12px;
            }}
        """)
        return panel

    def _build_quick_launch_cards(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(12)
        cards = [
            ("Start Scan", "Run duplicate scan", "▶", "scan"),
            ("Review Last Results", "Open review", "📋", "review"),
            ("History", "Deletion audits", "🕐", "history"),
            ("Themes", "Appearance", "🎨", "themes"),
            ("Settings", "Configuration", "⚙️", "settings"),
        ]
        for idx, (title, desc, icon, station_id) in enumerate(cards):
            btn = QPushButton(f"  {icon}  {title}")
            btn.setToolTip(desc)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(48)
            btn.clicked.connect(lambda checked=False, s=station_id: self.navigate_requested.emit(s))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {theme_token('panel')};
                    color: {theme_token('text')};
                    border: 1px solid {theme_token('line')};
                    border-radius: 10px;
                    font-size: 13px;
                    text-align: left;
                    padding: 10px 14px;
                }}
                QPushButton:hover {{ border-color: {theme_token('accent')}; }}
            """)
            row, col = idx // 2, idx % 2
            grid.addWidget(btn, row, col)
        return grid

    def _build_resume_card(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("ResumeCard")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 10)
        self._resume_btn = QPushButton("Resume last scan")
        self._resume_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._resume_btn.setEnabled(False)
        self._resume_btn.clicked.connect(self._on_resume)
        self._resume_label = QLabel("No interrupted scan to resume")
        self._resume_label.setStyleSheet(f"color: {theme_token('muted')}; font-size: 12px;")
        layout.addWidget(self._resume_btn)
        layout.addWidget(self._resume_label, 1)
        frame.setStyleSheet(f"""
            QFrame#ResumeCard {{
                background: {theme_token('surface')};
                border: 1px solid {theme_token('line')};
                border-radius: 10px;
            }}
        """)
        return frame

    def _on_resume(self) -> None:
        try:
            from cerebro.history.store import HistoryStore
            store = HistoryStore()
            payload = store.get_latest_resume_payload()
            if payload:
                self._bus.resume_scan_requested.emit(payload.to_dict())
                self.navigate_requested.emit("scan")
        except Exception:
            pass

    def _update_recent_scan_label(self) -> None:
        """Set recent scan summary from bus (last_scan_summary)."""
        summary = self._bus.get_last_scan_summary() or {}
        groups = int(summary.get("groups") or 0)
        root = str(summary.get("root") or "")
        if groups > 0 or root:
            root_short = (Path(root).name or root or "—") if root else "—"
            self._recent_label.setText(f"Recent scan: {groups} groups · {root_short}")
        else:
            self._recent_label.setText("Recent scan: Run a scan to see summary")

    def on_enter(self) -> None:
        """Refresh dashboard and resume availability when page is shown."""
        opts = self._bus.get_scan_options() or {}
        strategy = str(opts.get("scanner_tier") or opts.get("default_scanner_tier") or "turbo")
        if hasattr(self, "_strategy_label") and self._strategy_label:
            self._strategy_label.setText(f"Active scan strategy: {strategy}")
        self._update_recent_scan_label()
        try:
            from cerebro.history.store import HistoryStore
            store = HistoryStore()
            payload = store.get_latest_resume_payload()
            if hasattr(self, "_resume_btn") and self._resume_btn and hasattr(self, "_resume_label") and self._resume_label:
                if payload:
                    self._resume_btn.setEnabled(True)
                    self._resume_label.setText("Resume interrupted scan")
                else:
                    self._resume_btn.setEnabled(False)
                    self._resume_label.setText("No interrupted scan to resume")
        except Exception:
            if hasattr(self, "_resume_btn"):
                self._resume_btn.setEnabled(False)
            if hasattr(self, "_resume_label"):
                self._resume_label.setText("No interrupted scan to resume")

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData() and event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        if event.mimeData() and event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile()
                if path:
                    self.folder_added.emit(path)
                    self.navigate_requested.emit("scan")
            event.acceptProposedAction()
