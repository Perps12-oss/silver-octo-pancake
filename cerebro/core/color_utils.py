# cerebro/core/color_utils.py
"""
Color Utilities — foundation for the Cerebro v2 theme system.

Pure Python color math. No framework dependencies (no Qt, no Tkinter).
Every function accepts and returns hex color strings.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple


# =============================================================================
# Hex Validation & Normalization
# =============================================================================

_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def validate_hex(hex_color: str) -> bool:
    """Return True if *hex_color* is a valid hex color string."""
    if not isinstance(hex_color, str):
        return False
    return bool(_HEX_RE.match(hex_color.strip()))


def normalize_hex(hex_color: str, force_alpha: bool = False) -> str:
    """Normalize any hex notation to lowercase ``#rrggbb`` (or ``#rrggbbaa``).

    - ``'#FFF'``        → ``'#ffffff'``
    - ``'#fFfFfF'``    → ``'#ffffff'``
    - ``'#abcdef'``    → ``'#abcdef'``
    - ``'#12345678'``  → ``'#12345678'``

    Set *force_alpha=True* to always return 8-char (appends ``ff`` if no alpha).
    """
    s = hex_color.strip()
    if s.startswith("#"):
        s = s[1:]
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if force_alpha and len(s) == 6:
        s = s + "ff"
    return f"#{s.lower()}"


# =============================================================================
# Hex ↔ RGB Conversion
# =============================================================================

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert ``'#0A0E14'`` → ``(10, 14, 20)``.

    Accepts 3-char (``#RGB``), 6-char (``#RRGGBB``), and 8-char
    (``#RRGGBBAA``) formats.  Alpha channel is discarded.
    """
    s = normalize_hex(hex_color)[1:]     # strip '#'
    # Handle both 6-char (#rrggbb) and 8-char (#rrggbbaa) formats
    s = s[:6]
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert ``(10, 14, 20)`` → ``'#0a0e14'``.

    Values are clamped to 0–255.
    """
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_to_rgba(hex_color: str) -> Tuple[int, int, int, int]:
    """Convert ``'#0A0E1480'`` → ``(10, 14, 20, 128)``.

    If no alpha is present, returns 255.
    """
    s = normalize_hex(hex_color)[1:]    # strip '#'
    r, g, b = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    a = int(s[6:8], 16) if len(s) >= 8 else 255
    return r, g, b, a


def rgba_to_hex(r: int, g: int, b: int, a: int = 255) -> str:
    """Convert ``(10, 14, 20, 128)`` → ``'#0a0e1480'``."""
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    a = max(0, min(255, int(a)))
    return f"#{r:02x}{g:02x}{b:02x}{a:02x}"


# =============================================================================
# Luminance & Contrast (WCAG 2.0)
# =============================================================================

def _linearize(c: float) -> float:
    """Convert sRGB component to linear light."""
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    """Return relative luminance per WCAG 2.0 (0.0 – 1.0).

    https://www.w3.org/TR/WCAG20/#relativeluminancedef
    """
    r, g, b = hex_to_rgb(hex_color)
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def contrast_ratio(fg: str, bg: str) -> float:
    """WCAG 2.0 contrast ratio.  1.0 = identical, 21.0 = black on white.

    4.5 : 1 = AA pass for normal text.
    3.0 : 1 = AA pass for large text (18px+ bold or 24px+).
    """
    l1 = luminance(fg)
    l2 = luminance(bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def ensure_contrast(fg: str, bg: str, min_ratio: float = 4.5) -> str:
    """Adjust *fg* until it meets *min_ratio* contrast against *bg*.

    If the foreground is too close to the background, lighten or darken it
    iteratively until the ratio is met.  Returns the adjusted hex color.
    """
    if contrast_ratio(fg, bg) >= min_ratio:
        return fg

    bg_lum = luminance(bg)

    # Decide direction: push fg toward the opposite end of luminance scale.
    # If bg is dark, make fg lighter.  If bg is light, make fg darker.
    if bg_lum < 0.5:
        step = lighten
    else:
        step = darken

    current = fg
    for i in range(200):
        if contrast_ratio(current, bg) >= min_ratio:
            return current
        # Adaptive step: small adjustments at first, larger if stuck
        pct = 2 if i < 50 else 5 if i < 100 else 10
        current = step(current, pct)

    return current                  # best effort


# =============================================================================
# Lighten / Darken
# =============================================================================

def lighten(hex_color: str, percent: int) -> str:
    """Lighten a color by *percent* percent.

    Blends each channel toward 255 (white). Uses ``round()`` so
    ``lighten('#000000', 50)`` → ``'#808080'``.
    """
    percent = max(0, min(100, int(percent)))
    r, g, b = hex_to_rgb(hex_color)
    nr = r + (255 - r) * percent / 100
    ng = g + (255 - g) * percent / 100
    nb = b + (255 - b) * percent / 100
    return rgb_to_hex(round(nr), round(ng), round(nb))


def darken(hex_color: str, percent: int) -> str:
    """Darken a color by *percent* percent.

    ``darken('#ffffff', 50)`` → ``'#808080'``.
    """
    percent = max(0, min(100, int(percent)))
    r, g, b = hex_to_rgb(hex_color)
    nr = r * (100 - percent) / 100
    ng = g * (100 - percent) / 100
    nb = b * (100 - percent) / 100
    return rgb_to_hex(round(nr), round(ng), round(nb))


# =============================================================================
# Alpha
# =============================================================================

def with_alpha(hex_color: str, alpha_percent: int) -> str:
    """Return the color with an alpha channel as an 8-char hex.

    ``with_alpha('#E6EDF3', 60)`` → ``'#e6edf399'``.
    *alpha_percent* is 0 (transparent) – 100 (opaque).
    """
    alpha = max(0, min(255, int(255 * alpha_percent / 100)))
    r, g, b = hex_to_rgb(hex_color)
    return rgba_to_hex(r, g, b, alpha)


def alpha_to_int(alpha_hex: str) -> int:
    """Extract the alpha byte from an 8-char hex color.

    ``alpha_to_int('#e6edf399')`` → ``153``.
    Returns 255 if no alpha present.
    """
    _, _, _, a = hex_to_rgba(alpha_hex)
    return a


# =============================================================================
# Blend
# =============================================================================

def blend(color_a: str, color_b: str, ratio: float) -> str:
    """Linearly blend two colors.

    ``ratio=0.0`` → all *color_a*, ``ratio=1.0`` → all *color_b*.
    ``ratio=0.5`` → midpoint.
    """
    ratio = max(0.0, min(1.0, float(ratio)))
    r1, g1, b1 = hex_to_rgb(color_a)
    r2, g2, b2 = hex_to_rgb(color_b)
    r = round(r1 + (r2 - r1) * ratio)
    g = round(g1 + (g2 - g1) * ratio)
    b = round(b1 + (b2 - b1) * ratio)
    return rgb_to_hex(r, g, b)


# =============================================================================
# Derive Helpers (used by theme schema resolution)
# =============================================================================

def derive(lighten_pct: Optional[int] = None,
           darken_pct: Optional[int] = None,
           alpha_pct: Optional[int] = None) -> str:
    """Derive a color from a base using the given operations.

    This is a convenience function used by the theme schema resolver.
    The actual base color is passed separately.

    Returns a string describing the derivation (used internally).
    """
    # This function is informational — actual derivation is done by
    # the calling code using the specific functions above.
    parts = []
    if lighten_pct is not None:
        parts.append(f"lighten:{lighten_pct}")
    if darken_pct is not None:
        parts.append(f"darken:{darken_pct}")
    if alpha_pct is not None:
        parts.append(f"alpha:{alpha_pct}")
    return "+".join(parts) if parts else "identity"


def apply_derive(base: str, derive_str: str) -> str:
    """Apply a derive specification to a base color.

    *derive_str* format (from ``ColorSlot.derive_fn``):
    - ``"lighten:8"``   — lighten by 8%
    - ``"darken:10"``   — darken by 10%
    - ``"alpha:50"``    — set alpha to 50%
    - ``"alpha:50"``    — set alpha to 50%

    Multiple operations separated by ``+``: ``"darken:10+alpha:80"``
    """
    if not derive_str:
        return base

    result = base
    for part in derive_str.split("+"):
        part = part.strip()
        if not part or ":" not in part:
            continue
        fn_name, value = part.split(":", 1)
        try:
            amount = int(value)
        except ValueError:
            continue

        if fn_name == "lighten":
            result = lighten(result, amount)
        elif fn_name == "darken":
            result = darken(result, amount)
        elif fn_name == "alpha":
            result = with_alpha(result, amount)

    return result


# =============================================================================
# Utility
# =============================================================================

def is_dark(hex_color: str) -> bool:
    """Return True if the perceived luminance is below 0.5 (dark surface)."""
    return luminance(hex_color) < 0.5


def is_light(hex_color: str) -> bool:
    """Return True if the perceived luminance is 0.5 or above (light surface)."""
    return luminance(hex_color) >= 0.5


def invert(hex_color: str) -> str:
    """Invert a color (255 - channel). Useful for guaranteed contrast testing."""
    r, g, b = hex_to_rgb(hex_color)
    return rgb_to_hex(255 - r, 255 - g, 255 - b)


# =============================================================================
# Constants — semantic feedback colors used as defaults in theme resolution
# =============================================================================

SUCCESS = "#3FB950"
WARNING = "#D29922"
DANGER = "#F85149"
INFO = "#58A6FF"


__all__ = [
    # Validation
    "validate_hex", "normalize_hex",
    # Conversion
    "hex_to_rgb", "rgb_to_hex", "hex_to_rgba", "rgba_to_hex",
    # Luminance & contrast
    "luminance", "contrast_ratio", "ensure_contrast",
    # Adjustments
    "lighten", "darken", "with_alpha", "alpha_to_int",
    "blend", "invert",
    # Derive helpers
    "derive", "apply_derive",
    # Utility
    "is_dark", "is_light",
    # Constants
    "SUCCESS", "WARNING", "DANGER", "INFO",
]
