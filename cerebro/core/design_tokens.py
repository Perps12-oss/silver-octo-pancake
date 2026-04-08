# cerebro/core/design_tokens.py
"""
Cerebro v2 Design Tokens - Single Source of Truth

All UI colors, typography, spacing, and other design values
are defined here. This ensures consistency across all components.

Color Palette:
- Dark navy + cyan design system (Ashisoft-inspired)
- High contrast for accessibility
- Semantic colors for actions (success, danger, warning)

Usage:
    from cerebro.core import DesignTokens
    bg_color = DesignTokens.bg_primary
    accent_color = DesignTokens.accent
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final


# ============================================================================
# Design Tokens Dataclass
# ============================================================================


@dataclass(frozen=True)
class DesignTokens:
    """
    Immutable container for all design tokens.

    All values are final - create a new instance if you need
    different colors (e.g., for theme switching).
    """

    # -------------------------------------------------------------------------
    # Color Palette - Backgrounds
    # -------------------------------------------------------------------------

    # Primary window background
    bg_primary: Final[str] = "#0A0E14"

    # Panel backgrounds (side panels, cards, dialogs)
    bg_secondary: Final[str] = "#0D1117"

    # Row/card backgrounds within panels
    bg_tertiary: Final[str] = "#161B22"

    # Input fields and dropdowns
    bg_input: Final[str] = "#0D1117"

    # -------------------------------------------------------------------------
    # Color Palette - Accents & Actions
    # -------------------------------------------------------------------------

    # Active tabs, selected items, primary buttons
    accent: Final[str] = "#22D3EE"

    # Button hover states
    accent_hover: Final[str] = "#06B6D4"

    # Delete buttons, error states
    danger: Final[str] = "#F85149"

    # Scan complete, space saved
    success: Final[str] = "#3FB950"

    # Warnings, protected folders
    warning: Final[str] = "#D29922"

    # Info messages, help text
    info: Final[str] = "#58A6FF"

    # -------------------------------------------------------------------------
    # Color Palette - Text
    # -------------------------------------------------------------------------

    # Primary text (headings, labels)
    text_primary: Final[str] = "#E6EDF3"

    # Secondary/muted text (descriptions, hints)
    text_secondary: Final[str] = "#8B949E"

    # Text on accent backgrounds
    text_on_accent: Final[str] = "#FFFFFF"

    # Disabled text
    text_disabled: Final[str] = "#484F58"

    # -------------------------------------------------------------------------
    # Color Palette - Borders & Dividers
    # -------------------------------------------------------------------------

    # Panel borders, dividers, outlines
    border: Final[str] = "#30363D"

    # Subtle dividers within panels
    border_subtle: Final[str] = "#21262D"

    # -------------------------------------------------------------------------
    # Color Palette - Special
    # -------------------------------------------------------------------------

    # Duplicate group header background
    group_header: Final[str] = "#1C2333"

    # Alternating row color for readability
    row_alternate: Final[str] = "#0C1118"

    # Checkbox checked state
    checkbox_checked: Final[str] = "#22D3EE"

    # Checkbox unchecked state
    checkbox_unchecked: Final[str] = "#484F58"

    # -------------------------------------------------------------------------
    # Typography - Font Sizes (pixels)
    # -------------------------------------------------------------------------

    font_size_large: Final[int] = 16
    font_size_default: Final[int] = 13
    font_size_small: Final[int] = 11
    font_size_tiny: Final[int] = 10

    # Font families (ordered by preference)
    font_family_default: Final[str] = "Segoe UI"
    font_family_monospace: Final[str] = "Cascadia Code, Consolas, monospace"

    # -------------------------------------------------------------------------
    # Spacing - Pixels
    # -------------------------------------------------------------------------

    spacing_xs: Final[int] = 4
    spacing_sm: Final[int] = 8
    spacing_md: Final[int] = 12
    spacing_lg: Final[int] = 16
    spacing_xl: Final[int] = 24

    # -------------------------------------------------------------------------
    # Layout - Minimum Sizes
    # -------------------------------------------------------------------------

    min_window_width: Final[int] = 1024
    min_window_height: Final[int] = 700

    min_left_panel_width: Final[int] = 200
    min_preview_panel_height: Final[int] = 200

    # -------------------------------------------------------------------------
    # Layout - Default Panel Proportions (0.0-1.0)
    # -------------------------------------------------------------------------

    left_panel_proportion: Final[float] = 0.25  # 25% of width
    preview_panel_proportion: Final[float] = 0.30  # 30% of height

    # -------------------------------------------------------------------------
    # Borders - Radius (pixels)
    # -------------------------------------------------------------------------

    border_radius_sm: Final[int] = 4
    border_radius_md: Final[int] = 8
    border_radius_lg: Final[int] = 12

    # -------------------------------------------------------------------------
    # Animation - Durations (milliseconds)
    # -------------------------------------------------------------------------

    animation_fast: Final[int] = 150
    animation_default: Final[int] = 250
    animation_slow: Final[int] = 400

    # -------------------------------------------------------------------------
    # Icon Sizes (pixels)
    # -------------------------------------------------------------------------

    icon_size_sm: Final[int] = 16
    icon_size_md: Final[int] = 20
    icon_size_lg: Final[int] = 24


# ============================================================================
# Default Instance (used throughout the application)
# ============================================================================

# Single immutable instance for the default dark theme
tokens = DesignTokens()


# ============================================================================
# Theme Variants (optional future use)
# ============================================================================


class LightTheme(DesignTokens):
    """Light theme variant - for future theme switching support."""

    bg_primary: Final[str] = "#FFFFFF"
    bg_secondary: Final[str] = "#F6F8FA"
    bg_tertiary: Final[str] = "#E8ECF0"
    text_primary: Final[str] = "#1F2937"
    text_secondary: Final[str] = "#6B7280"
    border: Final[str] = "#D1D5DB"


class SolarizedTheme(DesignTokens):
    """Solarized theme variant."""

    bg_primary: Final[str] = "#002B36"
    bg_secondary: Final[str] = "#073642"
    bg_tertiary: Final[str] = "#094554"
    accent: Final[str] = "#2AA198"
    text_primary: Final[str] = "#839496"
    text_secondary: Final[str] = "#586E75"
    border: Final[str] = "#002836"


# ============================================================================
# Helper Functions
# ============================================================================


def get_color(name: str, theme: str = "dark") -> str:
    """
    Get a color by name.

    Args:
        name: Color token name (e.g., "bg_primary", "accent")
        theme: Theme name ("dark", "light", "solarized")

    Returns:
        Hex color string.
    """
    theme_map = {
        "dark": tokens,
        "light": LightTheme(),
        "solarized": SolarizedTheme(),
    }
    t = theme_map.get(theme, tokens)
    return getattr(t, name, tokens.bg_primary)


def set_theme(name: str) -> None:
    """
    Set the active theme globally.

    Note: This is a placeholder for future theme switching.
    Currently only "dark" (the default) is fully implemented.
    """
    # Future: update global tokens instance
    # Future: emit theme change signal
    pass
