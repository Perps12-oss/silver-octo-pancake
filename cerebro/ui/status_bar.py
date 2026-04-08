# cerebro/ui/status_bar.py
"""
Cerebro v2 Status Bar Component

Bottom status bar showing live scan metrics:
- Files Scanned: Number of files processed
- Duplicates: Number of duplicate files found
- Groups: Number of duplicate groups found
- Reclaimable: Total space that can be freed
- Elapsed: Time since scan started

Design: Horizontal bar with segmented labels and optional progress bar.
Updated via periodic polling during active scans.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

try:
    import customtkinter as ctk
except ImportError:
    ctk = None

from cerebro.core import DesignTokens


# ============================================================================
# Status Dataclass
# ============================================================================


@dataclass
class StatusBarData:
    """Data to display in status bar."""

    files_scanned: int = 0
    duplicates_found: int = 0
    groups_found: int = 0
    bytes_reclaimable: int = 0
    elapsed_seconds: float = 0.0
    current_file: str = ""
    is_scanning: bool = False

    @property
    def reclaimable_human(self) -> str:
        """Format bytes reclaimable as human-readable."""
        return self._format_bytes(self.bytes_reclaimable)

    @property
    def elapsed_human(self) -> str:
        """Format elapsed time as human-readable."""
        if self.elapsed_seconds < 60:
            return f"{self.elapsed_seconds:.1f}s"
        elif self.elapsed_seconds < 3600:
            minutes = int(self.elapsed_seconds / 60)
            secs = int(self.elapsed_seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(self.elapsed_seconds / 3600)
            minutes = int((self.elapsed_seconds % 3600) / 60)
            return f"{hours}h {minutes}m"

    @staticmethod
    def _format_bytes(size: int) -> str:
        """Format byte count as human-readable."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"


# ============================================================================
# Status Bar Component
# ============================================================================


class StatusBar:
    """
    Bottom status bar component for Cerebro v2 main window.

    Displays real-time metrics during scanning and final results.
    """

    def __init__(self, parent: Optional[ctk.CTk] = None) -> None:
        """
        Initialize status bar.

        Args:
            parent: Parent CTk widget
        """
        if ctk is None:
            raise ImportError("customtkinter is required for Cerebro v2 UI")

        self._parent = parent
        self._frame: Optional[ctk.CTkFrame] = None

        # Data
        self._data = StatusBarData()

        # Widgets
        self._label_files: Optional[ctk.CTkLabel] = None
        self._label_duplicates: Optional[ctk.CTkLabel] = None
        self._label_groups: Optional[ctk.CTkLabel] = None
        self._label_reclaimable: Optional[ctk.CTkLabel] = None
        self._label_elapsed: Optional[ctk.CTkLabel] = None
        self._progress_bar: Optional[ctk.CTkProgressBar] = None
        self._label_current_file: Optional[ctk.CTkLabel] = None
        self._label_message: Optional[ctk.CTkLabel] = None

    def build(self) -> ctk.CTkFrame:
        """
        Build and return the status bar frame.

        Returns:
            CTkFrame containing all status labels and progress bar.
        """
        self._frame = ctk.CTkFrame(
            master=self._parent,
            fg_color=DesignTokens.bg_secondary,
            height=35,
        )

        # Use grid layout
        self._frame.grid_columnconfigure((0, 1, 2), weight=0)  # Left labels
        self._frame.grid_columnconfigure(3, weight=0)  # Separator
        self._frame.grid_columnconfigure(4, weight=0)  # Groups
        self._frame.grid_columnconfigure(5, weight=0)  # Separator
        self._frame.grid_columnconfigure(6, weight=1)  # Reclaimable
        self._frame.grid_columnconfigure((7, 8), weight=0)  # Right labels
        self._frame.grid_columnconfigure(9, weight=0)  # Progress bar

        # Label style
        label_style = {
            "font": (DesignTokens.font_family_default, DesignTokens.font_size_small),
            "text_color": DesignTokens.text_secondary,
        }

        separator_style = {
            "font": (DesignTokens.font_family_default, DesignTokens.font_size_tiny),
            "text_color": DesignTokens.border,
        }

        # Create labels
        self._create_labels(label_style, separator_style)

        return self._frame

    def _create_labels(self, label_style: dict, separator_style: dict) -> None:
        """Create all status bar labels."""
        # [ Files: ]
        self._label_files = ctk.CTkLabel(
            master=self._frame,
            text="Scanned: 0",
            anchor="e",
            **label_style,
        )
        self._label_files.grid(row=0, column=0, padx=DesignTokens.spacing_md, pady=DesignTokens.spacing_sm)

        # Separator
        sep1 = ctk.CTkLabel(master=self._frame, text="|", **separator_style)
        sep1.grid(row=0, column=1, padx=DesignTokens.spacing_xs)

        # [ Duplicates: ]
        self._label_duplicates = ctk.CTkLabel(
            master=self._frame,
            text="Dupes: 0",
            anchor="e",
            **label_style,
        )
        self._label_duplicates.grid(row=0, column=2, padx=DesignTokens.spacing_md, pady=DesignTokens.spacing_sm)

        # Separator
        sep2 = ctk.CTkLabel(master=self._frame, text="|", **separator_style)
        sep2.grid(row=0, column=3, padx=DesignTokens.spacing_xs)

        # [ Groups: ]
        self._label_groups = ctk.CTkLabel(
            master=self._frame,
            text="Groups: 0",
            anchor="e",
            **label_style,
        )
        self._label_groups.grid(row=0, column=4, padx=DesignTokens.spacing_md, pady=DesignTokens.spacing_sm)

        # Separator
        sep3 = ctk.CTkLabel(master=self._frame, text="|", **separator_style)
        sep3.grid(row=0, column=5, padx=DesignTokens.spacing_xs)

        # [ Reclaimable: ]
        self._label_reclaimable = ctk.CTkLabel(
            master=self._frame,
            text="Reclaimable: 0 B",
            anchor="e",
            **label_style,
        )
        self._label_reclaimable.grid(row=0, column=6, padx=DesignTokens.spacing_md, pady=DesignTokens.spacing_sm)

        # Separator
        sep4 = ctk.CTkLabel(master=self._frame, text="|", **separator_style)
        sep4.grid(row=0, column=7, padx=DesignTokens.spacing_xs)

        # Progress bar (pulsing during scan)
        self._progress_bar = ctk.CTkProgressBar(
            master=self._frame,
            width=100,
            height=20,
            progress_color=DesignTokens.accent,
        )
        self._progress_bar.grid(row=0, column=8, padx=DesignTokens.spacing_md, pady=DesignTokens.spacing_sm)

        # Separator
        sep5 = ctk.CTkLabel(master=self._frame, text="|", **separator_style)
        sep5.grid(row=0, column=9, padx=DesignTokens.spacing_xs)

        # [ Elapsed: ] - on next row
        self._label_elapsed = ctk.CTkLabel(
            master=self._frame,
            text="Elapsed: 0:00",
            anchor="e",
            **label_style,
        )
        self._label_elapsed.grid(row=1, column=0, columnspan=2, padx=DesignTokens.spacing_md, pady=DesignTokens.spacing_xs)

        # Current file - on next row
        self._label_current_file = ctk.CTkLabel(
            master=self._frame,
            text="",
            anchor="w",
            **label_style,
        )
        self._label_current_file.grid(row=1, column=2, columnspan=7, padx=DesignTokens.spacing_md, pady=DesignTokens.spacing_xs)

        # Status message - on next row
        self._label_message = ctk.CTkLabel(
            master=self._frame,
            text="Ready",
            anchor="w",
            **label_style,
        )
        self._label_message.grid(row=1, column=9, padx=DesignTokens.spacing_md, pady=DesignTokens.spacing_xs)

    # -------------------------------------------------------------------------
    # Data Updates
    # -------------------------------------------------------------------------

    def update(self, data: StatusBarData) -> None:
        """
        Update status bar with new data.

        Args:
            data: New status bar data
        """
        self._data = data
        self._update_labels()

    def _update_labels(self) -> None:
        """Update all labels with current data."""
        # Update numeric labels
        self._label_files.configure(text=f"Scanned: {self._data.files_scanned:,}")
        self._label_duplicates.configure(text=f"Dupes: {self._data.duplicates_found:,}")
        self._label_groups.configure(text=f"Groups: {self._data.groups_found:,}")
        self._label_reclaimable.configure(text=f"Reclaimable: {self._data.reclaimable_human}")
        self._label_elapsed.configure(text=f"Elapsed: {self._data.elapsed_human}")

        # Update progress bar
        if self._data.is_scanning:
            # Show progress bar
            self._progress_bar.grid()
            # Calculate progress (0-100)
            # This is a simple approximation - real progress comes from engine
            progress = 50  # Pulsing effect during scan
            self._progress_bar.set(progress)

            # Update current file
            if self._data.current_file:
                display = self._data.current_file
                if len(display) > 40:
                    display = "..." + display[-40:]
                self._label_current_file.configure(text=display)
            else:
                self._label_current_file.configure(text="")
        else:
            # Hide progress bar
            self._progress_bar.grid_forget()
            self._label_current_file.configure(text="")

    # -------------------------------------------------------------------------
    # Individual Updates
    # -------------------------------------------------------------------------

    def set_files_scanned(self, count: int) -> None:
        """Update files scanned count."""
        self._data.files_scanned = count
        self._update_labels()

    def set_duplicates_found(self, count: int) -> None:
        """Update duplicates found count."""
        self._data.duplicates_found = count
        self._update_labels()

    def set_groups_found(self, count: int) -> None:
        """Update groups found count."""
        self._data.groups_found = count
        self._update_labels()

    def set_reclaimable(self, bytes: int) -> None:
        """Update bytes reclaimable."""
        self._data.bytes_reclaimable = bytes
        self._update_labels()

    def set_elapsed(self, seconds: float) -> None:
        """Update elapsed time."""
        self._data.elapsed_seconds = seconds
        self._update_labels()

    def set_current_file(self, path: str) -> None:
        """Update current file being processed."""
        self._data.current_file = path
        self._update_labels()

    def set_scanning(self, is_scanning: bool) -> None:
        """Set scan state (shows/hides progress bar)."""
        self._data.is_scanning = is_scanning
        self._update_labels()

    def update_scan_progress(
        self,
        files_scanned: int = 0,
        files_total: int = 0,
        duplicates_found: int = 0,
        groups_found: int = 0,
        bytes_reclaimable: int = 0,
        elapsed_seconds: float = 0.0,
        current_file: str = "",
    ) -> None:
        """
        Update all scan progress metrics at once.

        Args:
            files_scanned: Number of files processed
            files_total: Total files to process (0 if unknown)
            duplicates_found: Number of duplicates found
            groups_found: Number of groups found
            bytes_reclaimable: Total bytes that can be reclaimed
            elapsed_seconds: Time elapsed since scan start
            current_file: Name/path of current file being processed
        """
        self._data.files_scanned = files_scanned
        self._data.files_total = files_total
        self._data.duplicates_found = duplicates_found
        self._data.groups_found = groups_found
        self._data.bytes_reclaimable = bytes_reclaimable
        self._data.elapsed_seconds = elapsed_seconds
        self._data.current_file = current_file
        self._data.is_scanning = True
        self._update_labels()

    def set_message(self, message: str) -> None:
        """
        Set the status message text.

        Args:
            message: Status message to display
        """
        if self._label_message:
            self._label_message.configure(text=message)

    def reset(self) -> None:
        """Reset all values to zero/empty."""
        self._data = StatusBarData()
        self._update_labels()
        if self._label_message:
            self._label_message.configure(text="Ready")

    def get_frame(self) -> Optional[ctk.CTkFrame]:
        """Return the status bar frame."""
        return self._frame


__all__ = ["StatusBar", "StatusBarData"]
