# cerebro/ui/mode_tabs.py
"""
Cerebro v2 Mode Tabs Component

Individual button-style tabs for selecting scan mode:
- Files - SHA256 byte-level duplicate detection
- Photos - pHash + dHash perceptual similarity
- Videos - Frame extraction + comparison
- Music - ID3 tag fuzzy matching
- Empty Folders - Recursive empty directory finder
- Large Files - Size-ranked file listing

Design: Compact, left-aligned tabs with icons. Active tab has accent bottom border.
Emits callback when mode changes.
"""
from __future__ import annotations

from typing import Callable, Optional

try:
    import customtkinter as ctk
except ImportError:
    ctk = None

from cerebro.core import DesignTokens


# ============================================================================
# Mode Tabs Component
# ============================================================================


class ModeTabs:
    """
    Scan mode selector using individual button-style tabs.

    Modes: Files, Photos, Videos, Music, Empty Folders, Large Files
    Features:
    - Compact width (not stretched)
    - Left-aligned layout
    - Icon + text display
    - Accent bottom border on active tab
    """

    # Mode constants (for consistency across app)
    MODE_FILES = "files"
    MODE_PHOTOS = "photos"
    MODE_VIDEOS = "videos"
    MODE_MUSIC = "music"
    MODE_EMPTY_FOLDERS = "empty_folders"
    MODE_LARGE_FILES = "large_files"

    # All modes
    ALL_MODES = [
        MODE_FILES,
        MODE_PHOTOS,
        MODE_VIDEOS,
        MODE_MUSIC,
        MODE_EMPTY_FOLDERS,
        MODE_LARGE_FILES,
    ]

    # Display names with icons
    DISPLAY_NAMES: dict[str, str] = {
        MODE_FILES: "📄 Files",
        MODE_PHOTOS: "🖼 Photos",
        MODE_VIDEOS: "🎬 Videos",
        MODE_MUSIC: "🎵 Music",
        MODE_EMPTY_FOLDERS: "📁 Empty Folders",
        MODE_LARGE_FILES: "📊 Large Files",
    }

    def __init__(self, parent: Optional[ctk.CTk] = None) -> None:
        """
        Initialize mode tabs.

        Args:
            parent: Parent CTk widget
        """
        if ctk is None:
            raise ImportError("customtkinter is required for Cerebro v2 UI")

        self._parent = parent
        self._frame: Optional[ctk.CTkFrame] = None
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._current_mode = self.MODE_FILES

        # Callback
        self._on_mode_changed: Optional[Callable[[str], None]] = None

        # Track active button widget
        self._active_button: Optional[ctk.CTkButton] = None

    def build(self) -> ctk.CTkFrame:
        """
        Build and return the mode tabs frame.

        Returns:
            CTkFrame containing 6 compact, left-aligned mode buttons.
        """
        # Create frame for tabs
        self._frame = ctk.CTkFrame(
            master=self._parent,
            fg_color=DesignTokens.bg_secondary,
            corner_radius=0,
        )

        # Create individual buttons for each mode
        for mode in self.ALL_MODES:
            display_name = self.DISPLAY_NAMES[mode]

            # Create button with custom styling
            btn = ctk.CTkButton(
                master=self._frame,
                text=display_name,
                font=(DesignTokens.font_family_default, DesignTokens.font_size_default),
                fg_color="transparent",
                text_color=DesignTokens.text_secondary,
                hover_color=DesignTokens.bg_tertiary,
                corner_radius=0,
                border_width=0,
                anchor="w",
                padx=DesignTokens.spacing_md,
                pady=DesignTokens.spacing_sm,
                command=lambda m=mode: self._on_tab_click(m),
            )

            # Configure button to be compact (not expanded)
            btn.pack(side="left", padx=0, pady=0)

            # Store button reference
            self._buttons[mode] = btn

        # Set initial active state
        self._update_active_tab()

        return self._frame

    def _on_tab_click(self, mode: str) -> None:
        """
        Handle tab button click.

        Args:
            mode: Mode code of clicked tab
        """
        self._current_mode = mode
        self._update_active_tab()

        # Notify callback with mode code
        if self._on_mode_changed is not None:
            self._on_mode_changed(self._current_mode)

    def _update_active_tab(self) -> None:
        """Update visual state of all tabs to reflect current selection."""
        for mode, btn in self._buttons.items():
            if mode == self._current_mode:
                # Active tab styling
                btn.configure(
                    fg_color="transparent",
                    text_color=DesignTokens.accent,
                    border_width=2,
                    border_color=DesignTokens.accent,
                )
                # Position border at bottom
                btn._border_spacing = -2
                self._active_button = btn
            else:
                # Inactive tab styling
                btn.configure(
                    fg_color="transparent",
                    text_color=DesignTokens.text_secondary,
                    border_width=0,
                )

    # -------------------------------------------------------------------------
    # Callback Setter
    # -------------------------------------------------------------------------

    def set_on_mode_changed(self, callback: Callable[[str], None]) -> None:
        """
        Set callback when mode changes.

        Args:
            callback: Function receiving mode code (e.g., "files", "photos")
        """
        self._on_mode_changed = callback

    # -------------------------------------------------------------------------
    # Mode Control
    # -------------------------------------------------------------------------

    def set_mode(self, mode: str) -> None:
        """
        Programmatically set the active mode.

        Args:
            mode: Mode code (one of MODE_*)
        """
        if mode in self.ALL_MODES:
            self._current_mode = mode
            if self._buttons:
                self._update_active_tab()

    def get_mode(self) -> str:
        """Return the current mode code."""
        return self._current_mode

    def get_display_name(self) -> str:
        """Return the current mode display name."""
        return self.DISPLAY_NAMES.get(self._current_mode, "📄 Files")

    def get_widget(self) -> Optional[ctk.CTkFrame]:
        """Return the tabs frame widget."""
        return self._frame

    def is_mode_available(self, mode: str) -> bool:
        """
        Check if a mode is available.

        Args:
            mode: Mode code to check

        Returns:
            True if mode is in the list of available modes.
        """
        return mode in self.ALL_MODES


__all__ = [
    "ModeTabs",
    "MODE_FILES",
    "MODE_PHOTOS",
    "MODE_VIDEOS",
    "MODE_MUSIC",
    "MODE_EMPTY_FOLDERS",
    "MODE_LARGE_FILES",
]
