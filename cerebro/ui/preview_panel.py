# cerebro/ui/preview_panel.py
"""
Cerebro v2 Preview Panel Component

Collapsible bottom panel with side-by-side image comparison:
- Two image canvases with synchronized zoom/pan
- Metadata labels below each image (resolution, size, format, date, path)
- "Keep This" quick-action buttons for marking keepers
- Visual diff toggle (XOR overlay)

Design: Collapsible via Ctrl+P. Images can be synchronized zoomed.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import customtkinter as ctk
except ImportError:
    ctk = None

from cerebro.core import DesignTokens


# ============================================================================
# Preview Image Data
# ============================================================================


@dataclass
class PreviewImage:
    """Data about a previewed image."""

    path: Path
    resolution: str = ""
    size: str = ""
    format: str = ""
    modified: str = ""
    is_keeper: bool = False

    # EXIF data
    exif_camera: str = ""
    exif_iso: int = 0
    exif_focal: str = ""
    exif_date: str = ""
    has_exif: bool = False


# ============================================================================
# Preview Panel Component
# ============================================================================


class PreviewPanel:
    """
    Bottom collapsible panel for image preview and comparison.

    Shows two images side-by-side with synchronized zoom/pan.
    """

    def __init__(self, parent: Optional[ctk.CTk] = None) -> None:
        """
        Initialize preview panel.

        Args:
            parent: Parent CTk widget
        """
        if ctk is None:
            raise ImportError("customtkinter is required for Cerebro v2 UI")

        self._parent = parent
        self._frame: Optional[ctk.CTkFrame] = None
        self._expanded = True

        # Image data
        self._image_a: Optional[PreviewImage] = None
        self._image_b: Optional[PreviewImage] = None

        # Zoom/pan state
        self._zoom_level = 1.0
        self._pan_x = 0
        self._pan_y = 0

        # Callbacks
        self._on_keep_a: Optional[Callable[[], None]] = None
        self._on_keep_b: Optional[Callable[[], None]] = None

        # Widgets
        self._canvas_a: Optional[ctk.CTkCanvas] = None
        self._canvas_b: Optional[ctk.CTkCanvas] = None
        self._photo_a: Optional[ctk.CTkImage] = None
        self._photo_b: Optional[ctk.CTkImage] = None

        # Metadata labels
        self._meta_a: Dict[str, ctk.CTkLabel] = {}
        self._meta_b: Dict[str, ctk.CTkLabel] = {}

        # Toggle button
        self._btn_toggle: Optional[ctk.CTkButton] = None

        # Visual diff overlay toggle
        self._btn_diff: Optional[ctk.CTkButton] = None
        self._show_diff: bool = False
        self._diff_overlay: Optional[ctk.CTkImage] = None

    def build(self) -> ctk.CTkFrame:
        """
        Build and return the preview panel frame.

        Returns:
            CTkFrame with two image canvases and metadata.
        """
        self._frame = ctk.CTkFrame(
            master=self._parent,
            fg_color=DesignTokens.bg_primary,
        )

        # Header with collapse toggle
        self._create_header()

        # Content with two image panels side-by-side
        content = ctk.CTkFrame(master=self._frame, fg_color=DesignTokens.bg_primary)
        content.pack(fill="both", expand=True, padx=DesignTokens.spacing_md)

        # Two-column layout
        content.grid_columnconfigure(0, weight=1)  # Image A
        content.grid_columnconfigure(1, weight=1)  # Image B

        self._create_image_panel(content, 0, "A")
        self._create_image_panel(content, 1, "B")

        return self._frame

    def _create_header(self) -> None:
        """Create collapsible header."""
        header = ctk.CTkFrame(
            master=self._frame,
            fg_color=DesignTokens.bg_secondary,
            height=30,
        )

        # Title on left
        title = ctk.CTkLabel(
            master=header,
            text="Preview",
            anchor="w",
            font=(DesignTokens.font_family_default, DesignTokens.font_size_default, "bold"),
            text_color=DesignTokens.text_primary,
        )
        title.pack(side="left", padx=DesignTokens.spacing_md)

        # Visual diff toggle button
        self._btn_diff = ctk.CTkButton(
            master=header,
            text="Diff",
            width=50,
            height=25,
            fg_color=DesignTokens.bg_tertiary,
            text_color=DesignTokens.text_secondary,
            hover_color=DesignTokens.bg_input,
        )
        self._btn_diff.configure(command=self._toggle_diff)
        self._btn_diff.pack(side="right", padx=DesignTokens.spacing_sm)

        # Collapse button on right
        self._btn_toggle = ctk.CTkButton(
            master=header,
            text="▼",
            width=30,
            height=25,
            fg_color=DesignTokens.bg_tertiary,
            text_color=DesignTokens.text_secondary,
            hover_color=DesignTokens.bg_input,
        )
        self._btn_toggle.configure(command=self._toggle)
        self._btn_toggle.pack(side="right", padx=DesignTokens.spacing_sm)

        header.pack(fill="x")

    def _create_image_panel(self, parent: ctk.CTkFrame, col: int, label: str) -> None:
        """
        Create a single image panel (canvas + metadata).

        Args:
            parent: Parent frame
            col: Grid column (0 for A, 1 for B)
            label: Label ("A" or "B")
        """
        panel = ctk.CTkFrame(
            master=parent,
            fg_color=DesignTokens.bg_primary,
        )
        panel.grid(row=0, column=col, sticky="nsew", padx=DesignTokens.spacing_sm)

        # Canvas for image (CTkCanvas subclasses tk.Canvas — use `bg`, not CTk's `bg_color`)
        canvas_height = 200
        canvas = ctk.CTkCanvas(
            master=panel,
            width=300,
            height=canvas_height,
            bg=DesignTokens.bg_tertiary,
            highlightthickness=0,
        )
        if label == "A":
            self._canvas_a = canvas
        else:
            self._canvas_b = canvas
        canvas.pack(fill="both", expand=True)

        # Metadata row below canvas
        meta_frame = ctk.CTkFrame(master=panel, fg_color=DesignTokens.bg_primary)
        meta_frame.pack(fill="x", pady=(DesignTokens.spacing_sm, 0))

        # Create metadata labels
        self._meta_a[label] = {}

        meta_frame.grid_columnconfigure((0, 1), weight=0)  # Left labels
        meta_frame.grid_columnconfigure(2, weight=1)  # Values

        label_style = {
            "font": (DesignTokens.font_family_default, DesignTokens.font_size_tiny),
            "text_color": DesignTokens.text_secondary,
            "anchor": "w",
        }

        value_style = {
            "font": (DesignTokens.font_family_default, DesignTokens.font_size_tiny),
            "text_color": DesignTokens.text_primary,
            "anchor": "w",
        }

        # Format badge (small colored label)
        self._meta_a["format_badge"] = ctk.CTkLabel(
            master=meta_frame,
            text="—",
            font=(DesignTokens.font_family_default, DesignTokens.font_size_tiny),
            fg_color=DesignTokens.bg_tertiary,
            text_color=DesignTokens.text_secondary,
            corner_radius=4,
            padx=DesignTokens.spacing_xs,
        )
        self._meta_a["format_badge"].grid(row=0, column=0, padx=DesignTokens.spacing_xs)

        # Resolution
        self._meta_a["res_label"] = ctk.CTkLabel(
            master=meta_frame,
            text=f"{label} Resolution:",
            **label_style,
        )
        self._meta_a["res_label"].grid(row=1, column=0, padx=DesignTokens.spacing_xs)

        self._meta_a["res_value"] = ctk.CTkLabel(
            master=meta_frame,
            text="—",
            **value_style,
        )
        self._meta_a["res_value"].grid(row=1, column=2, padx=DesignTokens.spacing_xs, sticky="w")

        # Size
        self._meta_a["size_label"] = ctk.CTkLabel(
            master=meta_frame,
            text=f"{label} Size:",
            **label_style,
        )
        self._meta_a["size_label"].grid(row=2, column=0, padx=DesignTokens.spacing_xs)

        self._meta_a["size_value"] = ctk.CTkLabel(
            master=meta_frame,
            text="—",
            **value_style,
        )
        self._meta_a["size_value"].grid(row=2, column=2, padx=DesignTokens.spacing_xs, sticky="w")

        # Modified date
        self._meta_a["date_label"] = ctk.CTkLabel(
            master=meta_frame,
            text=f"{label} Modified:",
            **label_style,
        )
        self._meta_a["date_label"].grid(row=3, column=0, padx=DesignTokens.spacing_xs)

        self._meta_a["date_value"] = ctk.CTkLabel(
            master=meta_frame,
            text="—",
            **value_style,
        )
        self._meta_a["date_value"].grid(row=3, column=2, padx=DesignTokens.spacing_xs, sticky="w")

        # EXIF data row (camera, ISO, focal length)
        self._meta_a["exif_label"] = ctk.CTkLabel(
            master=meta_frame,
            text="EXIF:",
            **label_style,
        )
        self._meta_a["exif_label"].grid(row=4, column=0, padx=DesignTokens.spacing_xs)

        self._meta_a["exif_value"] = ctk.CTkLabel(
            master=meta_frame,
            text="—",
            **value_style,
        )
        self._meta_a["exif_value"].grid(row=4, column=2, padx=DesignTokens.spacing_xs, sticky="w")

        # Keep This button
        if col == 0:
            btn = ctk.CTkButton(
                master=meta_frame,
                text=f"Keep {label}",
                height=25,
                fg_color=DesignTokens.accent,
                text_color=DesignTokens.text_on_accent,
                font=(DesignTokens.font_family_default, DesignTokens.font_size_tiny),
            )
            if self._on_keep_a is not None:
                btn.configure(command=self._on_keep_a)
            btn.grid(row=5, column=0, columnspan=3, pady=(DesignTokens.spacing_sm, 0))
        else:
            self._meta_a["keep_btn"] = ctk.CTkButton(
                master=meta_frame,
                text=f"Keep {label}",
                height=25,
                fg_color=DesignTokens.accent,
                text_color=DesignTokens.text_on_accent,
                font=(DesignTokens.font_family_default, DesignTokens.font_size_tiny),
            )
            if self._on_keep_b is not None:
                self._meta_a["keep_btn"].configure(command=self._on_keep_b)
            self._meta_a["keep_btn"].grid(row=5, column=0, columnspan=3, pady=(DesignTokens.spacing_sm, 0))

    def _toggle(self) -> None:
        """Toggle panel visibility."""
        self._expanded = not self._expanded

        if self._btn_toggle:
            self._btn_toggle.configure(text="▼" if self._expanded else "▶")

        if self._frame:
            if self._expanded:
                self._frame.grid()
            else:
                self._frame.grid_forget()

    # -------------------------------------------------------------------------
    # Image Loading
    # -------------------------------------------------------------------------

    def load_image(self, path: Path, is_side: str = "A", exif_data: Optional[dict] = None) -> None:
        """
        Load an image into the preview panel.

        Args:
            path: Path to image file
            is_side: "A" or "B" for which side to load
            exif_data: Optional EXIF data from engine
        """
        try:
            from PIL import Image, ImageTk

            # Load and resize image (thumbnail for display)
            img = Image.open(path)

            # Get format for badge
            format_str = img.format.upper() if img.format else "UNKNOWN"
            ext = path.suffix.upper() if path.suffix else ""

            # Determine badge color
            badge_color = DesignTokens.bg_tertiary
            if format_str == "JPEG":
                badge_color = DesignTokens.bg_tertiary
            elif format_str == "PNG":
                badge_color = "#2D4F46"  # Green
            elif format_str in ("HEIC", "HEIF"):
                badge_color = "#E74C3C"  # Red
            elif ext in (".CR2", ".CR3", ".NEF", ".ARW", ".DNG"):
                badge_color = "#F97316"  # Orange

            # Get metadata
            data = PreviewImage(
                path=path,
                resolution=f"{img.width} × {img.height}",
                size=f"{img.size / 1024 / 1024:.1f} MB",
                format=format_str,
            )

            # Add EXIF data if provided
            if exif_data:
                data.exif_camera = exif_data.get("exif_camera", "")
                data.exif_iso = exif_data.get("exif_iso", 0)
                data.exif_focal = exif_data.get("exif_focal", "")
                data.exif_date = exif_data.get("exif_date", "")
                data.has_exif = exif_data.get("has_exif", False)

            # Format EXIF display string
            if data.has_exif:
                exif_parts = []
                if data.exif_camera:
                    exif_parts.append(data.exif_camera)
                if data.exif_iso:
                    exif_parts.append(f"ISO {data.exif_iso}")
                if data.exif_focal:
                    exif_parts.append(data.exif_focal)
                exif_str = " | ".join(exif_parts) if exif_parts else "No EXIF"
            else:
                exif_str = "No EXIF"

            # Create thumbnail (max 400px dimension)
            img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)

            if is_side == "A":
                self._image_a = data
                self._photo_a = photo
                if self._canvas_a:
                    self._canvas_a.delete("all")
                    self._canvas_a.create_image(0, 0, image=photo, anchor="center")
                self._update_metadata_a(data, format_str, badge_color, exif_str)
            else:
                self._image_b = data
                self._photo_b = photo
                if self._canvas_b:
                    self._canvas_b.delete("all")
                    self._canvas_b.create_image(0, 0, image=photo, anchor="center")
                self._update_metadata_b(data, format_str, badge_color, exif_str)

        except Exception as e:
            # Show error message if image can't be loaded
            self._show_error(f"Cannot load image: {e}", is_side)

    def _show_error(self, message: str, is_side: str) -> None:
        """Show error message in place of image."""
        if is_side == "A":
            if self._canvas_a:
                self._canvas_a.delete("all")
                self._canvas_a.create_text(
                    150, 100,
                    text=message,
                    fill=DesignTokens.danger,
                    font=(DesignTokens.font_family_default, DesignTokens.font_size_small),
                )
        else:
            if self._canvas_b:
                self._canvas_b.delete("all")
                self._canvas_b.create_text(
                    150, 100,
                    text=message,
                    fill=DesignTokens.danger,
                    font=(DesignTokens.font_family_default, DesignTokens.font_size_small),
                )

    def _update_metadata_a(self, data: PreviewImage, format_str: str, badge_color: str, exif_str: str) -> None:
        """Update metadata labels for side A."""
        self._meta_a["format_badge"].configure(text=format_str or "—")
        self._meta_a["format_badge"].configure(fg_color=badge_color)

        self._meta_a["res_value"].configure(text=data.resolution or "—")
        self._meta_a["size_value"].configure(text=data.size or "—")

        # Use EXIF date if available
        if data.has_exif and data.exif_date:
            self._meta_a["date_value"].configure(text=data.exif_date)
        else:
            from datetime import datetime
            if hasattr(data, 'modified') and data.modified:
                dt = datetime.fromtimestamp(data.modified)
                self._meta_a["date_value"].configure(text=dt.strftime("%Y-%m-%d %H:%M"))
            else:
                self._meta_a["date_value"].configure(text="—")

        self._meta_a["exif_value"].configure(text=exif_str)

    def _update_metadata_b(self, data: PreviewImage, format_str: str, badge_color: str, exif_str: str) -> None:
        """Update metadata labels for side B."""
        self._meta_b["format_badge"].configure(text=format_str or "—")
        self._meta_b["format_badge"].configure(fg_color=badge_color)

        self._meta_b["res_value"].configure(text=data.resolution or "—")
        self._meta_b["size_value"].configure(text=data.size or "—")

        # Use EXIF date if available
        if data.has_exif and data.exif_date:
            self._meta_b["date_value"].configure(text=data.exif_date)
        else:
            from datetime import datetime
            if hasattr(data, 'modified') and data.modified:
                dt = datetime.fromtimestamp(data.modified)
                self._meta_b["date_value"].configure(text=dt.strftime("%Y-%m-%d %H:%M"))
            else:
                self._meta_b["date_value"].configure(text="—")

        self._meta_b["exif_value"].configure(text=exif_str)

    def clear(self) -> None:
        """Clear both image previews."""
        if self._canvas_a:
            self._canvas_a.delete("all")
            self._canvas_a.delete("diff_overlay")
            self._image_a = None
            self._reset_metadata_a()

        if self._canvas_b:
            self._canvas_b.delete("all")
            self._image_b = None
            self._reset_metadata_b()

        self._show_diff = False
        self._diff_overlay = None

    def _reset_metadata_a(self) -> None:
        """Reset metadata labels for side A to defaults."""
        self._meta_a["format_badge"].configure(text="—")
        self._meta_a["format_badge"].configure(fg_color=DesignTokens.bg_tertiary)
        self._meta_a["res_value"].configure(text="—")
        self._meta_a["size_value"].configure(text="—")
        self._meta_a["date_value"].configure(text="—")
        self._meta_a["exif_value"].configure(text="—")

    def _reset_metadata_b(self) -> None:
        """Reset metadata labels for side B to defaults."""
        self._meta_b["res_value"].configure(text="—")
        self._meta_b["format_badge"].configure(text="—")
        self._meta_b["format_badge"].configure(fg_color=DesignTokens.bg_tertiary)
        self._meta_b["size_value"].configure(text="—")
        self._meta_b["date_value"].configure(text="—")
        self._meta_b["exif_value"].configure(text="—")

    def _toggle_diff(self) -> None:
        """Toggle visual diff overlay."""
        self._show_diff = not self._show_diff

        if self._btn_diff:
            if self._show_diff:
                self._btn_diff.configure(text="Hide Diff", fg_color=DesignTokens.accent)
            else:
                self._btn_diff.configure(text="Diff", fg_color=DesignTokens.bg_tertiary)

        # Apply or remove diff overlay
        if self._show_diff and self._photo_a and self._photo_b:
            self._show_diff_overlay()
        else:
            self._hide_diff_overlay()

    def _show_diff_overlay(self) -> None:
        """Show XOR difference overlay between the two images."""
        if not self._canvas_a or not self._canvas_b:
            return

        try:
            from PIL import Image, ImageTk, Chops

            # Load both images at full resolution
            img_a_path = self._image_a.path if self._image_a else None
            img_b_path = self._image_b.path if self._image_b else None

            if not img_a_path or not img_b_path:
                return

            img_a = Image.open(img_a_path)
            img_b = Image.open(img_b_path)

            # Resize to same dimensions
            size = (min(img_a.width, img_b.width), min(img_a.height, img_b.height))
            img_a = img_a.resize(size, Image.LANCZOS)
            img_b = img_b.resize(size, Image.LANCZOS)

            # Compute difference (XOR-like using difference mode)
            diff = Chops.difference(img_a, img_b)

            # Create red overlay (highlight differences)
            diff_rgba = diff.convert("RGBA")
            pixels = list(diff_rgba.getdata())

            # Enhance differences with red tint
            enhanced_pixels = []
            for r, g, b, a in pixels:
                # If pixel is different (not black), make it reddish
                if r > 10 or g > 10 or b > 10:
                    enhanced_pixels.append((255, 100, 100, 150))  # Semi-transparent red
                else:
                    enhanced_pixels.append((0, 0, 0, 0))  # Transparent black

            # Apply to overlay image
            overlay = Image.new("RGBA", size)
            overlay.putdata(enhanced_pixels)

            # Create thumbnail for canvas
            overlay.thumbnail((400, 400), Image.LANCZOS)
            self._diff_overlay = ImageTk.PhotoImage(overlay)

            # Draw overlay on canvas A
            self._canvas_a.delete("diff_overlay")
            self._canvas_a.create_image(0, 0, image=self._diff_overlay, anchor="center", tags="diff_overlay")

        except Exception:
            pass  # Diff overlay is optional, don't break if it fails

    def _hide_diff_overlay(self) -> None:
        """Hide the diff overlay."""
        if self._canvas_a:
            self._canvas_a.delete("diff_overlay")
        self._diff_overlay = None

    # -------------------------------------------------------------------------
    # Callback Setters
    # -------------------------------------------------------------------------

    def set_on_keep_a(self, callback: Callable[[], None]) -> None:
        """Set callback for Keep A button."""
        self._on_keep_a = callback

    def set_on_keep_b(self, callback: Callable[[], None]) -> None:
        """Set callback for Keep B button."""
        self._on_keep_b = callback

    # -------------------------------------------------------------------------
    # State Control
    # -------------------------------------------------------------------------

    def set_expanded(self, expanded: bool) -> None:
        """
        Set panel expanded state.

        Args:
            expanded: If True, panel is visible; if False, hidden.
        """
        self._expanded = expanded

        if self._btn_toggle:
            self._btn_toggle.configure(text="▼" if expanded else "▶")

        if self._frame:
            if expanded:
                self._frame.grid()
            else:
                self._frame.grid_forget()

    def is_expanded(self) -> bool:
        """Return current expanded state."""
        return self._expanded

    def get_frame(self) -> Optional[ctk.CTkFrame]:
        """Return the preview panel frame."""
        return self._frame


__all__ = ["PreviewPanel", "PreviewImage"]
