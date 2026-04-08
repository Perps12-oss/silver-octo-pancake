# cerebro/ui/toolbar.py
"""
Cerebro v2 Toolbar Component

Top toolbar containing all primary action buttons with Ashisoft-style labeled buttons:
- [📁 Add Folders] - Add folder to scan list
- [✕ Remove] - Remove selected folder
- [▶ Search Now] - Begin scanning (accent color)
- [⏹ Stop] - Cancel running scan (hidden until scan starts)
- [📋 Auto Mark ▼] - Auto-mark dropdown menu
- [🗑 Delete] - Delete marked items (danger color)
- [📦 Move To] - Move marked items to folder
- [⚙ Settings] - Open settings dialog
- [❓ Help] - Show help/information

Design: Horizontal row of labeled buttons with icons, grouped with visual separators.
"""
from __future__ import annotations

from typing import Callable, Optional

try:
    import customtkinter as ctk
except ImportError:
    ctk = None

from cerebro.core import DesignTokens


# ============================================================================
# Tooltip Helper
# ============================================================================


class Tooltip:
    """Simple tooltip implementation for CustomTkinter widgets."""

    def __init__(self, widget: ctk.CTkBaseWidget, text: str) -> None:
        """
        Initialize tooltip.

        Args:
            widget: The widget to attach tooltip to
            text: Tooltip text to display
        """
        self.widget = widget
        self.text = text
        self.tip_window: Optional[ctk.Toplevel] = None

        # Bind mouse events
        widget.bind("<Enter>", self._show_tip)
        widget.bind("<Leave>", self._hide_tip)

    def _show_tip(self, event: Optional[object] = None) -> None:
        """Show the tooltip window."""
        if self.tip_window or not self.widget.winfo_exists():
            return

        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25

        self.tip_window = ctk.CTkToplevel()
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        self.tip_window.attributes("-topmost", True)

        label = ctk.CTkLabel(
            master=self.tip_window,
            text=self.text,
            fg_color="#1C2333",
            text_color=DesignTokens.text_primary,
            corner_radius=4,
            padx=8,
            pady=4,
            font=(DesignTokens.font_family_default, DesignTokens.font_size_small),
        )
        label.pack()

    def _hide_tip(self, event: Optional[object] = None) -> None:
        """Hide the tooltip window."""
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


# ============================================================================
# Toolbar Component
# ============================================================================


class Toolbar:
    """
    Top toolbar component for Cerebro v2 main window.

    All buttons emit callback signals when clicked.
    Features Ashisoft-style labeled buttons with icons.
    """

    def __init__(self, parent: Optional[ctk.CTk] = None) -> None:
        """
        Initialize toolbar.

        Args:
            parent: Parent CTk widget (usually the main window)
        """
        if ctk is None:
            raise ImportError("customtkinter is required for Cerebro v2 UI")

        self._parent = parent
        self._frame: Optional[ctk.CTkFrame] = None

        # Callbacks
        self._on_add_path: Optional[Callable[[], None]] = None
        self._on_remove: Optional[Callable[[], None]] = None
        self._on_start: Optional[Callable[[], None]] = None
        self._on_stop: Optional[Callable[[], None]] = None
        self._on_settings: Optional[Callable[[], None]] = None
        self._on_help: Optional[Callable[[], None]] = None
        self._on_auto_mark: Optional[Callable[[], None]] = None
        self._on_delete: Optional[Callable[[], None]] = None
        self._on_move_to: Optional[Callable[[], None]] = None

        # Button references
        self._btn_add: Optional[ctk.CTkButton] = None
        self._btn_remove: Optional[ctk.CTkButton] = None
        self._btn_start: Optional[ctk.CTkButton] = None
        self._btn_stop: Optional[ctk.CTkButton] = None
        self._btn_auto_mark: Optional[ctk.CTkButton] = None
        self._btn_delete: Optional[ctk.CTkButton] = None
        self._btn_move_to: Optional[ctk.CTkButton] = None
        self._btn_settings: Optional[ctk.CTkButton] = None
        self._btn_help: Optional[ctk.CTkButton] = None

    def build(self) -> ctk.CTkFrame:
        """
        Build and return the toolbar frame.

        Returns:
            CTkFrame containing all toolbar buttons.
        """
        self._frame = ctk.CTkFrame(
            master=self._parent,
            fg_color=DesignTokens.bg_primary,
            height=50,
            corner_radius=0,
        )

        # Configure columns with weights
        # Column layout: 0:spacer, 1:group1, 2:separator, 3:group2, 4:spacer
        self._frame.grid_columnconfigure(0, weight=1)  # Spacer left
        self._frame.grid_columnconfigure(1, weight=0)  # Group 1 buttons
        self._frame.grid_columnconfigure(2, weight=0)  # Separator
        self._frame.grid_columnconfigure(3, weight=0)  # Group 2 buttons
        self._frame.grid_columnconfigure(4, weight=1)  # Spacer right

        # Create button groups
        self._create_group1_buttons()
        self._create_separator(column=2)
        self._create_group2_buttons()

        return self._frame

    def _create_separator(self, column: int) -> None:
        """
        Create a vertical separator line between button groups.

        Args:
            column: Grid column to place separator in
        """
        separator = ctk.CTkFrame(
            master=self._frame,
            width=1,
            fg_color=DesignTokens.border,
        )
        separator.grid(row=0, column=column, padx=DesignTokens.spacing_lg, sticky="ns")

    def _create_group1_buttons(self) -> None:
        """Create first group of buttons: Add Folders, Remove, Search Now, Stop."""
        # Common button styling
        base_kwargs = {
            "height": 36,
            "corner_radius": DesignTokens.border_radius_md,
            "font": (DesignTokens.font_family_default, DesignTokens.font_size_default),
            "fg_color": DesignTokens.bg_secondary,
            "text_color": DesignTokens.text_primary,
            "hover_color": DesignTokens.bg_tertiary,
        }

        # Primary button styling (accent color)
        primary_kwargs = base_kwargs.copy()
        primary_kwargs.update({
            "fg_color": DesignTokens.accent,
            "text_color": DesignTokens.text_on_accent,
            "hover_color": DesignTokens.accent_hover,
        })

        # Danger button styling (red)
        danger_kwargs = base_kwargs.copy()
        danger_kwargs.update({
            "fg_color": DesignTokens.danger,
            "text_color": DesignTokens.text_on_accent,
            "hover_color": "#D9453F",
        })

        # [📁 Add Folders]
        self._btn_add = ctk.CTkButton(
            master=self._frame,
            text="  📁 Add Folders  ",
            width=130,
            **base_kwargs,
        )
        self._btn_add.grid(row=0, column=1, padx=DesignTokens.spacing_sm, pady=DesignTokens.spacing_md)
        Tooltip(self._btn_add, "Add folders to scan list")

        # [✕ Remove]
        self._btn_remove = ctk.CTkButton(
            master=self._frame,
            text="  ✕ Remove  ",
            width=100,
            **base_kwargs,
        )
        self._btn_remove.grid(row=0, column=1, padx=DesignTokens.spacing_sm, pady=DesignTokens.spacing_md)
        Tooltip(self._btn_remove, "Remove selected folder from list")

        # [▶ Search Now] - Primary accent color
        self._btn_start = ctk.CTkButton(
            master=self._frame,
            text="  ▶ Search Now  ",
            width=140,
            **primary_kwargs,
        )
        self._btn_start.grid(row=0, column=1, padx=DesignTokens.spacing_sm, pady=DesignTokens.spacing_md)
        Tooltip(self._btn_start, "Start scanning for duplicates")

        # [⏹ Stop] - Danger color, hidden initially
        self._btn_stop = ctk.CTkButton(
            master=self._frame,
            text="  ⏹ Stop  ",
            width=100,
            state="disabled",
            **danger_kwargs,
        )
        self._btn_stop.grid(row=0, column=1, padx=DesignTokens.spacing_sm, pady=DesignTokens.spacing_md)
        Tooltip(self._btn_stop, "Stop scanning")

        # Wire up callbacks
        if self._on_add_path is not None:
            self._btn_add.configure(command=self._on_add_path)
        if self._on_remove is not None:
            self._btn_remove.configure(command=self._on_remove)
        if self._on_start is not None:
            self._btn_start.configure(command=self._on_start)
        if self._on_stop is not None:
            self._btn_stop.configure(command=self._on_stop)

    def _create_group2_buttons(self) -> None:
        """Create second group of buttons: Auto Mark, Delete, Move To, Settings, Help."""
        # Common button styling
        base_kwargs = {
            "height": 36,
            "corner_radius": DesignTokens.border_radius_md,
            "font": (DesignTokens.font_family_default, DesignTokens.font_size_default),
            "fg_color": DesignTokens.bg_secondary,
            "text_color": DesignTokens.text_primary,
            "hover_color": DesignTokens.bg_tertiary,
        }

        # Danger button styling (red)
        danger_kwargs = base_kwargs.copy()
        danger_kwargs.update({
            "fg_color": DesignTokens.danger,
            "text_color": DesignTokens.text_on_accent,
            "hover_color": "#D9453F",
        })

        # [📋 Auto Mark ▼]
        self._btn_auto_mark = ctk.CTkButton(
            master=self._frame,
            text="  📋 Auto Mark ▼  ",
            width=120,
            **base_kwargs,
        )
        self._btn_auto_mark.grid(row=0, column=3, padx=DesignTokens.spacing_sm, pady=DesignTokens.spacing_md)
        Tooltip(self._btn_auto_mark, "Auto-mark duplicate files")

        # [🗑 Delete] - Danger color
        self._btn_delete = ctk.CTkButton(
            master=self._frame,
            text="  🗑 Delete  ",
            width=100,
            **danger_kwargs,
        )
        self._btn_delete.grid(row=0, column=3, padx=DesignTokens.spacing_sm, pady=DesignTokens.spacing_md)
        Tooltip(self._btn_delete, "Delete marked files")

        # [📦 Move To]
        self._btn_move_to = ctk.CTkButton(
            master=self._frame,
            text="  📦 Move To  ",
            width=110,
            **base_kwargs,
        )
        self._btn_move_to.grid(row=0, column=3, padx=DesignTokens.spacing_sm, pady=DesignTokens.spacing_md)
        Tooltip(self._btn_move_to, "Move marked files to another folder")

        # [⚙ Settings]
        self._btn_settings = ctk.CTkButton(
            master=self._frame,
            text="  ⚙ Settings  ",
            width=110,
            **base_kwargs,
        )
        self._btn_settings.grid(row=0, column=3, padx=DesignTokens.spacing_sm, pady=DesignTokens.spacing_md)
        Tooltip(self._btn_settings, "Open settings dialog")

        # [❓ Help]
        self._btn_help = ctk.CTkButton(
            master=self._frame,
            text="  ❓ Help  ",
            width=90,
            **base_kwargs,
        )
        self._btn_help.grid(row=0, column=3, padx=DesignTokens.spacing_sm, pady=DesignTokens.spacing_md)
        Tooltip(self._btn_help, "Show help and information")

        # Wire up callbacks
        if self._on_auto_mark is not None:
            self._btn_auto_mark.configure(command=self._on_auto_mark)
        if self._on_delete is not None:
            self._btn_delete.configure(command=self._on_delete)
        if self._on_move_to is not None:
            self._btn_move_to.configure(command=self._on_move_to)
        if self._on_settings is not None:
            self._btn_settings.configure(command=self._on_settings)
        if self._on_help is not None:
            self._btn_help.configure(command=self._on_help)

    # -------------------------------------------------------------------------
    # Callback Setters
    # -------------------------------------------------------------------------

    def set_on_add_path(self, callback: Callable[[], None]) -> None:
        """Set callback for Add Folders button."""
        self._on_add_path = callback
        if self._btn_add is not None:
            self._btn_add.configure(command=callback)

    def set_on_remove(self, callback: Callable[[], None]) -> None:
        """Set callback for Remove button."""
        self._on_remove = callback
        if self._btn_remove is not None:
            self._btn_remove.configure(command=callback)

    def set_on_start(self, callback: Callable[[], None]) -> None:
        """Set callback for Search Now button."""
        self._on_start = callback
        if self._btn_start is not None:
            self._btn_start.configure(command=callback)

    def set_on_stop(self, callback: Callable[[], None]) -> None:
        """Set callback for Stop button."""
        self._on_stop = callback
        if self._btn_stop is not None:
            self._btn_stop.configure(command=callback)

    def set_on_settings(self, callback: Callable[[], None]) -> None:
        """Set callback for Settings button."""
        self._on_settings = callback
        if self._btn_settings is not None:
            self._btn_settings.configure(command=callback)

    def set_on_help(self, callback: Callable[[], None]) -> None:
        """Set callback for Help button."""
        self._on_help = callback
        if self._btn_help is not None:
            self._btn_help.configure(command=callback)

    def set_on_auto_mark(self, callback: Callable[[], None]) -> None:
        """Set callback for Auto Mark button."""
        self._on_auto_mark = callback
        if self._btn_auto_mark is not None:
            self._btn_auto_mark.configure(command=callback)

    def set_on_delete(self, callback: Callable[[], None]) -> None:
        """Set callback for Delete button."""
        self._on_delete = callback
        if self._btn_delete is not None:
            self._btn_delete.configure(command=callback)

    def set_on_move_to(self, callback: Callable[[], None]) -> None:
        """Set callback for Move To button."""
        self._on_move_to = callback
        if self._btn_move_to is not None:
            self._btn_move_to.configure(command=callback)

    # -------------------------------------------------------------------------
    # State Control
    # -------------------------------------------------------------------------

    def set_scanning(self, is_scanning: bool) -> None:
        """
        Update button states based on scan state.

        Args:
            is_scanning: True if scan is in progress
        """
        if self._btn_start is not None:
            self._btn_start.configure(state="disabled" if is_scanning else "normal")
        if self._btn_stop is not None:
            self._btn_stop.configure(state="normal" if is_scanning else "disabled")

        # Show/hide stop button by managing visibility
        if self._btn_stop is not None:
            if is_scanning:
                self._btn_stop.grid()
            else:
                self._btn_stop.grid_remove()

    def get_frame(self) -> Optional[ctk.CTkFrame]:
        """Return the toolbar frame."""
        return self._frame


__all__ = ["Toolbar"]
