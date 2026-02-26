from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QListWidget
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from cerebro.ui.pages.base_station import BaseStation
from cerebro.ui.theme_engine import ThemeEngine
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class StartScanConfig:
    """Backward-compatible config expected by StationNavigator/pages package.

    Keep this minimal; ScanPage/Controller can expand it later.
    """
    roots: List[str] = field(default_factory=list)
    mode: str = "turbo"  # turbo/ultra/quantum/etc (string for compatibility)
    include_hidden: bool = False
    follow_symlinks: bool = False
    file_globs: Optional[List[str]] = None


class StartPage(BaseStation):
    station_id = "mission"
    station_title = "Home"
    navigate_requested = Signal(str)
    folder_added = Signal(str)  # new for sidebar

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._build_gemini_ui()

    def _build_gemini_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # LEFT SIDEBAR — Gemini locations (persistent)
        sidebar = QFrame()
        sidebar.setFixedWidth(280)
        sidebar.setObjectName("LocationsSidebar")
        sb_layout = QVBoxLayout(sidebar)
        loc_label = QLabel("Locations")
        loc_label.setToolTip("Recently added scan roots. Click + Add Folder to start a scan.")
        sb_layout.addWidget(loc_label)
        self.locations_list = QListWidget()
        self.locations_list.setToolTip("Double-click a location to scan again")
        sb_layout.addWidget(self.locations_list)
        add_btn = QPushButton("+ Add Folder")
        add_btn.setToolTip("Choose a folder to scan for duplicates (opens Scan page)")
        add_btn.clicked.connect(lambda: self.navigate_requested.emit("scan"))
        sb_layout.addWidget(add_btn)
        layout.addWidget(sidebar)

        # CENTER HERO — Gemini drag-drop (12px rounded, teal accent feel)
        hero = QFrame()
        hero.setObjectName("HeroDropZone")
        hero.setStyleSheet("""
            QFrame#HeroDropZone {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #151922, stop:1 #0f1115);
                border: 2px dashed #262c3a;
                border-radius: 20px;
            }
            QFrame#HeroDropZone:hover { border-color: #00C4B4; }
        """)
        hero.setToolTip("Drop folders here to add them for scanning, or click Browse Computer")
        h_layout = QVBoxLayout(hero)
        h_layout.setAlignment(Qt.AlignCenter)
        icon = QLabel("📁")
        icon.setStyleSheet("font-size: 120px;")
        h_layout.addWidget(icon)
        h_layout.addWidget(QLabel("Drop folders or files here"))
        h_layout.addWidget(QLabel("or"))
        btn = QPushButton("Browse Computer")
        btn.setToolTip("Open Scan page to choose a folder and start duplicate scan")
        btn.clicked.connect(lambda: self.navigate_requested.emit("scan"))
        h_layout.addWidget(btn)
        layout.addWidget(hero, 1)

    # OPTIONAL: basic drop handlers (safe defaults)
    def dragEnterEvent(self, event: QDragEnterEvent):
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        # Minimal: if you later want to parse dropped folders/files, we can add it properly.
        event.acceptProposedAction()
