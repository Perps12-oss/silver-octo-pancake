# cerebro/ui/selection_bar.py
"""
Cerebro v2 Selection Assistant Bar Component

Horizontal strip below results for duplicate selection management:
- Rule dropdown: 8+ auto-mark rules (except newest, except largest, etc.)
- Apply button: Execute selected rule
- Selection counter: "X of Y selected"
- Select All / Deselect All / Invert buttons
- Delete Selected: Primary action button (danger color)

Design: Compact horizontal bar with clear visual hierarchy.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

try:
    import customtkinter as ctk
except ImportError:
    ctk = None

from cerebro.core import DesignTokens


# ============================================================================
# Selection Rules
# ============================================================================


class SelectionRules:
    """All available selection assistant rules."""

    # Rule identifiers
    RULE_EXCEPT_NEWEST = "except_newest"
    RULE_EXCEPT_OLDEST = "except_oldest"
    RULE_EXCEPT_LARGEST = "except_largest"
    RULE_EXCEPT_SMALLEST = "except_smallest"
    RULE_EXCEPT_HIGHEST_RES = "except_highest_res"
    RULE_IN_FOLDER = "in_folder"
    RULE_BY_EXTENSION = "by_extension"
    RULE_EXCEPT_FIRST = "except_first"
    RULE_INVERT = "invert"
    RULE_CLEAR = "clear"
    RULE_SELECT_ALL = "select_all"

    # Display names for dropdown
    DISPLAY_NAMES: Dict[str, str] = {
        RULE_EXCEPT_NEWEST: "Select all except newest",
        RULE_EXCEPT_OLDEST: "Select all except oldest",
        RULE_EXCEPT_LARGEST: "Select all except largest",
        RULE_EXCEPT_SMALLEST: "Select all except smallest",
        RULE_EXCEPT_HIGHEST_RES: "Select all except highest resolution",
        RULE_IN_FOLDER: "Select all in folder…",
        RULE_BY_EXTENSION: "Select by extension…",
        RULE_EXCEPT_FIRST: "Select all except first in group",
    }


# ============================================================================
# Selection Bar Component
# ============================================================================


class SelectionBar:
    """
    Selection assistant bar for managing duplicate file selection.

    Provides:
    - Rule selection dropdown
    - Apply button
    - Selection counter
    - Select All / Deselect / Invert
    - Delete Selected button
    """

    def __init__(self, parent: Optional[ctk.CTk] = None) -> None:
        """
        Initialize selection bar.

        Args:
            parent: Parent CTk widget
        """
        if ctk is None:
            raise ImportError("customtkinter is required for Cerebro v2 UI")

        self._parent = parent
        self._frame: Optional[ctk.CTkFrame] = None

        # Data
        self._selected_count = 0
        self._total_count = 0

        # Callbacks
        self._on_apply_rule: Optional[Callable[[str], None]] = None
        self._on_select_all: Optional[Callable[[], None]] = None
        self._on_deselect_all: Optional[Callable[[], None]] = None
        self._on_invert: Optional[Callable[[], None]] = None
        self._on_delete: Optional[Callable[[], None]] = None

        # Widgets
        self._option_menu: Optional[ctk.CTkOptionMenu] = None
        self._btn_apply: Optional[ctk.CTkButton] = None
        self._label_counter: Optional[ctk.CTkLabel] = None
        self._btn_select_all: Optional[ctk.CTkButton] = None
        self._btn_deselect: Optional[ctk.CTkButton] = None
        self._btn_invert: Optional[ctk.CTkButton] = None
        self._btn_delete: Optional[ctk.CTkButton] = None

    def build(self) -> ctk.CTkFrame:
        """
        Build and return the selection bar frame.

        Returns:
            CTkFrame with all selection controls.
        """
        self._frame = ctk.CTkFrame(
            master=self._parent,
            fg_color=DesignTokens.bg_primary,
            height=50,
        )

        # Layout: [Rule ▼] [Apply] [counter] | [All] [Deselect] [Invert] | [Delete]
        self._frame.grid_columnconfigure(0, weight=0)  # Rule
        self._frame.grid_columnconfigure(1, weight=0)  # Apply
        self._frame.grid_columnconfigure(2, weight=0)  # Counter spacer
        self._frame.grid_columnconfigure(3, weight=1)  # Counter (spacer + counter + spacer)
        self._frame.grid_columnconfigure(4, weight=0)  # All
        self._frame.grid_columnconfigure(5, weight=0)  # Deselect
        self._frame.grid_columnconfigure(6, weight=0)  # Invert
        self._frame.grid_columnconfigure(7, weight=0)  # Delete spacer
        self._frame.grid_columnconfigure(8, weight=0)  # Delete

        self._create_widgets()

        return self._frame

    def _create_widgets(self) -> None:
        """Create all selection bar widgets."""
        button_style = {
            "height": 30,
            "corner_radius": DesignTokens.border_radius_md,
            "font": (DesignTokens.font_family_default, DesignTokens.font_size_small),
        }

        # Rule dropdown
        rule_options = list(SelectionRules.DISPLAY_NAMES.values())
        self._option_menu = ctk.CTkOptionMenu(
            master=self._frame,
            values=rule_options,
            width=220,
            height=30,
            dropdown_font=(DesignTokens.font_family_default, DesignTokens.font_size_small),
            button_color=DesignTokens.bg_input,
            button_hover_color=DesignTokens.bg_tertiary,
            dropdown_hover_color=DesignTokens.bg_tertiary,
            text_color=DesignTokens.text_primary,
            fg_color=DesignTokens.bg_tertiary,
        )
        self._option_menu.set(SelectionRules.DISPLAY_NAMES[SelectionRules.RULE_EXCEPT_LARGEST])
        self._option_menu.grid(row=0, column=0, padx=DesignTokens.spacing_md, pady=(5, 5))

        # Apply button
        self._btn_apply = ctk.CTkButton(
            master=self._frame,
            text="Apply",
            width=70,
            fg_color=DesignTokens.accent,
            text_color=DesignTokens.text_on_accent,
            hover_color=DesignTokens.accent_hover,
            **button_style,
        )
        if self._on_apply_rule is not None:
            self._btn_apply.configure(command=lambda: self._on_apply_rule(self._get_selected_rule()))
        self._btn_apply.grid(row=0, column=1, padx=DesignTokens.spacing_sm, pady=(5, 5))

        # Counter label
        self._label_counter = ctk.CTkLabel(
            master=self._frame,
            text="0 of 0 selected",
            font=(DesignTokens.font_family_default, DesignTokens.font_size_small),
            text_color=DesignTokens.text_secondary,
        )
        self._label_counter.grid(row=0, column=3, padx=DesignTokens.spacing_md, pady=(5, 5))

        # Separator
        sep = ctk.CTkLabel(
            master=self._frame,
            text="|",
            font=(DesignTokens.font_family_default, DesignTokens.font_size_tiny),
            text_color=DesignTokens.border,
        )
        sep.grid(row=0, column=4, padx=DesignTokens.spacing_xs, pady=(5, 5))

        # Select All
        self._btn_select_all = ctk.CTkButton(
            master=self._frame,
            text="Select All",
            width=80,
            fg_color=DesignTokens.bg_tertiary,
            text_color=DesignTokens.text_primary,
            hover_color=DesignTokens.bg_input,
            **button_style,
        )
        if self._on_select_all is not None:
            self._btn_select_all.configure(command=self._on_select_all)
        self._btn_select_all.grid(row=0, column=5, padx=DesignTokens.spacing_sm, pady=(5, 5))

        # Deselect
        self._btn_deselect = ctk.CTkButton(
            master=self._frame,
            text="Deselect",
            width=70,
            fg_color=DesignTokens.bg_tertiary,
            text_color=DesignTokens.text_primary,
            hover_color=DesignTokens.bg_input,
            **button_style,
        )
        if self._on_deselect_all is not None:
            self._btn_deselect.configure(command=self._on_deselect_all)
        self._btn_deselect.grid(row=0, column=6, padx=DesignTokens.spacing_sm, pady=(5, 5))

        # Invert
        self._btn_invert = ctk.CTkButton(
            master=self._frame,
            text="Invert",
            width=60,
            fg_color=DesignTokens.bg_tertiary,
            text_color=DesignTokens.text_primary,
            hover_color=DesignTokens.bg_input,
            **button_style,
        )
        if self._on_invert is not None:
            self._btn_invert.configure(command=self._on_invert)
        self._btn_invert.grid(row=0, column=7, padx=DesignTokens.spacing_sm, pady=(5, 5))

        # Delete button (primary action, danger color)
        delete_style = button_style.copy()
        delete_style.update({
            "width": 100,
            "fg_color": DesignTokens.danger,
            "text_color": DesignTokens.text_on_accent,
            "hover_color": "#D84545",
            "font": (DesignTokens.font_family_default, DesignTokens.font_size_small, "bold"),
        })
        self._btn_delete = ctk.CTkButton(
            master=self._frame,
            text="Delete Selected",
            **delete_style,
        )
        if self._on_delete is not None:
            self._btn_delete.configure(command=self._on_delete)
        self._btn_delete.grid(row=0, column=8, padx=DesignTokens.spacing_md, pady=(5, 5))

    def _get_selected_rule(self) -> str:
        """
        Get the currently selected rule code.

        Returns:
            Rule code (e.g., "except_newest")
        """
        selected_display = self._option_menu.get()
        for code, display in SelectionRules.DISPLAY_NAMES.items():
            if display == selected_display:
                return code
        return SelectionRules.RULE_EXCEPT_LARGEST  # Default fallback

    # -------------------------------------------------------------------------
    # Callback Setters
    # -------------------------------------------------------------------------

    def set_on_apply_rule(self, callback: Callable[[str], None]) -> None:
        """Set callback for Apply button."""
        self._on_apply_rule = callback

    def set_on_select_all(self, callback: Callable[[], None]) -> None:
        """Set callback for Select All button."""
        self._on_select_all = callback

    def set_on_deselect_all(self, callback: Callable[[], None]) -> None:
        """Set callback for Deselect button."""
        self._on_deselect_all = callback

    def set_on_invert(self, callback: Callable[[], None]) -> None:
        """Set callback for Invert button."""
        self._on_invert = callback

    def set_on_delete(self, callback: Callable[[], None]) -> None:
        """Set callback for Delete button."""
        self._on_delete = callback

    # -------------------------------------------------------------------------
    # State Updates
    # -------------------------------------------------------------------------

    def update_counter(self, selected: int, total: int) -> None:
        """
        Update the selection counter display.

        Args:
            selected: Number of files currently selected
            total: Total number of files
        """
        self._selected_count = selected
        self._total_count = total

        if self._label_counter:
            if total > 0:
                percent = (selected / total) * 100
                self._label_counter.configure(text=f"{selected} of {total} selected ({percent:.0f}%)")
            else:
                self._label_counter.configure(text=f"{selected} of {total} selected")

    def set_deleting(self, is_deleting: bool) -> None:
        """
        Enable/disable delete button during deletion operation.

        Args:
            is_deleting: True if deletion is in progress
        """
        if self._btn_delete:
            if is_deleting:
                self._btn_delete.configure(state="disabled", text="Deleting…")
            else:
                self._btn_delete.configure(state="normal", text="Delete Selected")

    def get_frame(self) -> Optional[ctk.CTkFrame]:
        """Return the selection bar frame."""
        return self._frame

    def get_selected_rule(self) -> str:
        """Return the currently selected rule code."""
        return self._get_selected_rule()


__all__ = [
    "SelectionBar",
    "SelectionRules",
]
