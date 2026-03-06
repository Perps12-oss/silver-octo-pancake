# cerebro/controllers/__init__.py
"""
Canonical controller package (Batch 5).
Live scan control logic: re-exported from ui.controllers for clean scan path.
"""

from cerebro.ui.controllers.live_scan_controller import (
    LiveScanController,
    ControllerConfig,
)

__all__ = ["LiveScanController", "ControllerConfig"]
