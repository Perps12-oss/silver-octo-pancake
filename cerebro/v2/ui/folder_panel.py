"""
Folder Panel Widget

Left panel with 3 collapsible sections:
- Scan Folders: folders to include in scan
- Protect Folders: folders excluded from deletion
- Scan Options: mode-specific options
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, ttk
from typing import Optional, Callable, List, Dict
from pathlib import Path

try:
    import customtkinter as ctk
    CTkFrame = ctk.CTkFrame
    CTkButton = ctk.CTkButton
    CTkLabel = ctk.CTkLabel
    CTkScrollableFrame = ctk.CTkScrollableFrame
    CTkOptionMenu = ctk.CTkOptionMenu
    CTkSlider = ctk.CTkSlider
    CTkCheckBox = ctk.CTkCheckBox
except ImportError:
    CTkFrame = tk.Frame
    CTkButton = tk.Button
    CTkLabel = tk.Label
    CTkScrollableFrame = tk.Frame  # Simple fallback
    CTkOptionMenu = tk.OptionMenu
    CTkSlider = tk.Scale
    CTkCheckBox = tk.Checkbutton

from cerebro.v2.core.design_tokens import Spacing, Typography, Dimensions
from cerebro.v2.core.theme_bridge_v2 import theme_color, subscribe_to_theme


class FolderEntry:
    """Represents a folder entry in the list."""

    def __init__(self, path: Path, index: int = 0):
        self.path = path
        self.index = index
        self.selected: bool = False


class CollapsibleSection(CTkFrame):
    """
    Collapsible section with header and content.

    Features:
    - Expand/collapse toggle
    - Header with title and count indicator
    - Content frame that hides/shows
    """

    def __init__(
        self,
        master=None,
        title: str = "",
        count: int = 0,
        accent_color: Optional[str] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)
        self._title = title
        self._count = count
        self._custom_accent = accent_color
        self._accent_color = accent_color or theme_color("base.foreground")
        self._expanded = True

        subscribe_to_theme(self, self._apply_theme)

        # Widgets
        self._header_frame: Optional[CTkFrame] = None
        self._title_label: Optional[CTkLabel] = None
        self._count_label: Optional[CTkLabel] = None
        self._toggle_btn: Optional[CTkButton] = None
        self._content_frame: Optional[CTkFrame] = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Build collapsible section UI."""
        # Header frame
        self._header_frame = CTkFrame(
            self,
            height=32,
            fg_color=self._accent_color if self._custom_accent else theme_color("base.backgroundTertiary")
        )
        self._header_frame.pack(fill="x")

        # Title label
        self._title_label = CTkLabel(
            self._header_frame,
            text=self._title,
            font=Typography.FONT_MD,
            text_color=self._accent_color
        )
        self._title_label.pack(side="left", padx=Spacing.MD)

        # Count label
        self._count_label = CTkLabel(
            self._header_frame,
            text=f"({self._count})",
            font=Typography.FONT_SM,
            text_color=theme_color("base.foregroundSecondary")
        )
        self._count_label.pack(side="left", padx=Spacing.XS)

        # Spacer
        spacer = CTkLabel(self._header_frame, text="")
        spacer.pack(side="left", expand=True)

        # Toggle button
        self._toggle_btn = CTkButton(
            self._header_frame,
            text="▼",
            width=28,
            height=28,
            font=Typography.FONT_SM,
            fg_color="transparent",
            hover_color=theme_color("base.backgroundElevated"),
            border_width=0,
            corner_radius=0
        )
        self._toggle_btn.pack(side="right")
        self._toggle_btn.configure(command=self._toggle)

        # Content frame
        self._content_frame = CTkFrame(
            self,
            fg_color=theme_color("base.backgroundTertiary")
        )
        self._content_frame.pack(fill="both", expand=True, padx=Spacing.XS)

    def _apply_theme(self) -> None:
        """Apply theme colors to all widgets."""
        if self._custom_accent:
            self._accent_color = self._custom_accent
        else:
            self._accent_color = theme_color("base.foreground")

        try:
            self._header_frame.configure(
                fg_color=self._accent_color if self._custom_accent else theme_color("base.backgroundTertiary")
            )
        except Exception:
            pass
        try:
            self._title_label.configure(text_color=self._accent_color)
        except Exception:
            pass
        try:
            self._count_label.configure(text_color=theme_color("base.foregroundSecondary"))
        except Exception:
            pass
        try:
            self._toggle_btn.configure(hover_color=theme_color("base.backgroundElevated"))
        except Exception:
            pass
        try:
            self._content_frame.configure(fg_color=theme_color("base.backgroundTertiary"))
        except Exception:
            pass

    def _toggle(self) -> None:
        """Toggle expand/collapse."""
        self._expanded = not self._expanded
        self._toggle_btn.configure(text="▼" if self._expanded else "▶")

        if self._expanded:
            self._content_frame.pack(fill="both", expand=True, padx=Spacing.XS)
        else:
            self._content_frame.pack_forget()

    def set_title(self, title: str) -> None:
        """Set section title."""
        self._title = title
        self._title_label.configure(text=title)

    def set_count(self, count: int) -> None:
        """Set item count."""
        self._count = count
        self._count_label.configure(text=f"({count})")

    def increment_count(self) -> None:
        """Increment item count."""
        self._count += 1
        self._count_label.configure(text=f"({self._count})")

    def decrement_count(self) -> None:
        """Decrement item count."""
        self._count = max(0, self._count - 1)
        self._count_label.configure(text=f"({self._count})")

    def set_expanded(self, expanded: bool) -> None:
        """Set expanded state."""
        if self._expanded != expanded:
            self._toggle()

    def is_expanded(self) -> bool:
        """Check if section is expanded."""
        return self._expanded

    def get_content_frame(self) -> CTkFrame:
        """Get the content frame for adding widgets."""
        return self._content_frame


class ScanFolderList(CTkScrollableFrame):
    """
    Scrollable list of scan folders with remove buttons.

    Features:
    - Folder path display
    - Remove (×) button per entry
    - Add folder button at bottom
    """

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        subscribe_to_theme(self, self._apply_theme)

        # State
        self._folders: List[Path] = []
        self._folder_widgets: Dict[Path, Dict[str, tk.Widget]] = {}

        # Callbacks
        self._on_folder_added: Optional[Callable[[Path], None]] = None
        self._on_folder_removed: Optional[Callable[[Path], None]] = None

        # Build UI
        self._build_ui()

    def _build_ui(self) -> None:
        """Build folder list UI."""
        # Configure scrollbar styling if available
        try:
            self.configure(
                fg_color=theme_color("base.backgroundTertiary"),
                scrollbar_fg_color=theme_color("panel.background"),
                scrollbar_button_color=theme_color("base.backgroundTertiary"),
                scrollbar_button_hover_color=theme_color("button.primary")
            )
        except AttributeError:
            pass

        # Add button
        self._add_btn = CTkButton(
            self,
            text="+ Add Folder",
            height=Dimensions.BUTTON_HEIGHT_MD,
            font=Typography.FONT_MD,
            fg_color=theme_color("button.primary"),
            hover_color=theme_color("button.primaryHover"),
            corner_radius=Spacing.BORDER_RADIUS_SM
        )
        self._add_btn.pack(fill="x", padx=Spacing.SM, pady=(0, Spacing.SM))
        self._add_btn.configure(command=self._trigger_add_folder)

    def _apply_theme(self) -> None:
        """Apply theme colors to all widgets."""
        try:
            self.configure(
                fg_color=theme_color("base.backgroundTertiary"),
                scrollbar_fg_color=theme_color("panel.background"),
                scrollbar_button_color=theme_color("base.backgroundTertiary"),
                scrollbar_button_hover_color=theme_color("button.primary")
            )
        except (AttributeError, Exception):
            pass
        try:
            self._add_btn.configure(
                fg_color=theme_color("button.primary"),
                hover_color=theme_color("button.primaryHover")
            )
        except Exception:
            pass
        # Update existing folder row widgets
        for path, widgets in self._folder_widgets.items():
            try:
                widgets["frame"].configure(fg_color=theme_color("base.backgroundElevated"))
            except Exception:
                pass
            try:
                widgets["label"].configure(text_color=theme_color("base.foreground"))
            except Exception:
                pass
            try:
                widgets["button"].configure(
                    fg_color=theme_color("base.foregroundSecondary"),
                    hover_color=theme_color("feedback.danger"),
                    text_color=theme_color("base.foreground")
                )
            except Exception:
                pass

    def _trigger_add_folder(self) -> None:
        """Trigger add folder dialog."""
        path = filedialog.askdirectory(title="Select folder to scan")
        if path:
            self.add_folder(Path(path))

    def add_folder(self, path: Path) -> None:
        """Add a folder to the list."""
        if path in self._folders:
            return

        self._folders.append(path)

        # Create folder entry row
        row_frame = CTkFrame(
            self,
            height=Dimensions.ROW_HEIGHT,
            fg_color=theme_color("base.backgroundElevated")
        )
        row_frame.pack(fill="x", padx=Spacing.SM, pady=(0, Spacing.XS))

        # Folder name label (truncated)
        folder_name = path.name if path.name else str(path)
        if len(folder_name) > 30:
            folder_name = folder_name[:27] + "..."

        name_label = CTkLabel(
            row_frame,
            text=folder_name,
            font=Typography.FONT_SM,
            text_color=theme_color("base.foreground"),
            anchor="w"
        )
        name_label.pack(side="left", padx=Spacing.SM, fill="x", expand=True)

        # Remove button
        remove_btn = CTkButton(
            row_frame,
            text="×",
            width=24,
            height=24,
            font=Typography.FONT_LG,
            fg_color=theme_color("base.foregroundSecondary"),
            hover_color=theme_color("feedback.danger"),
            text_color=theme_color("base.foreground"),
            corner_radius=Spacing.BORDER_RADIUS_SM
        )
        remove_btn.pack(side="right", padx=Spacing.SM)
        remove_btn.configure(command=lambda: self._remove_folder(path))

        # Store widgets reference
        self._folder_widgets[path] = {
            "frame": row_frame,
            "label": name_label,
            "button": remove_btn
        }

        # Notify callback
        if self._on_folder_added:
            self._on_folder_added(path)

    def _remove_folder(self, path: Path) -> None:
        """Remove a folder from the list."""
        if path not in self._folders:
            return

        self._folders.remove(path)

        # Remove widgets
        widgets = self._folder_widgets.pop(path, {})
        if widgets:
            widgets["frame"].destroy()

        # Notify callback
        if self._on_folder_removed:
            self._on_folder_removed(path)

    def clear_folders(self) -> None:
        """Clear all folders from the list."""
        for path in list(self._folders):
            self._remove_folder(path)

    def get_folders(self) -> List[Path]:
        """Get list of folders."""
        return self._folders.copy()

    def set_folders(self, folders: List[Path]) -> None:
        """Set folders list (replaces existing)."""
        self.clear_folders()
        for path in folders:
            self.add_folder(path)

    def on_folder_added(self, callback: Callable[[Path], None]) -> None:
        """Set callback for folder added."""
        self._on_folder_added = callback

    def on_folder_removed(self, callback: Callable[[Path], None]) -> None:
        """Set callback for folder removed."""
        self._on_folder_removed = callback


class ProtectFolderList(ScanFolderList):
    """
    Scrollable list of protected folders (warning accent).

    Files in these paths will never be auto-selected for deletion.
    """

    def _build_ui(self) -> None:
        """Build protect folder list UI."""
        # Configure scrollbar styling if available
        try:
            self.configure(
                fg_color=theme_color("base.backgroundTertiary"),
                scrollbar_fg_color=theme_color("panel.background"),
                scrollbar_button_color=theme_color("base.backgroundTertiary"),
                scrollbar_button_hover_color=theme_color("feedback.warning")
            )
        except AttributeError:
            pass

        # Add button
        self._add_btn = CTkButton(
            self,
            text="+ Add Protected Folder",
            height=Dimensions.BUTTON_HEIGHT_MD,
            font=Typography.FONT_SM,
            fg_color=theme_color("feedback.warning"),
            hover_color=theme_color("feedback.warning"),
            corner_radius=Spacing.BORDER_RADIUS_SM
        )
        self._add_btn.pack(fill="x", padx=Spacing.SM, pady=(0, Spacing.SM))
        self._add_btn.configure(command=self._trigger_add_folder)

    def _apply_theme(self) -> None:
        """Apply theme colors to all widgets."""
        try:
            self.configure(
                fg_color=theme_color("base.backgroundTertiary"),
                scrollbar_fg_color=theme_color("panel.background"),
                scrollbar_button_color=theme_color("base.backgroundTertiary"),
                scrollbar_button_hover_color=theme_color("feedback.warning")
            )
        except (AttributeError, Exception):
            pass
        try:
            self._add_btn.configure(
                fg_color=theme_color("feedback.warning"),
                hover_color=theme_color("feedback.warning")
            )
        except Exception:
            pass
        # Update existing folder row widgets
        for path, widgets in self._folder_widgets.items():
            try:
                widgets["frame"].configure(fg_color=theme_color("base.backgroundElevated"))
            except Exception:
                pass
            try:
                widgets["label"].configure(text_color=theme_color("base.foreground"))
            except Exception:
                pass
            try:
                widgets["button"].configure(
                    fg_color=theme_color("base.foregroundSecondary"),
                    hover_color=theme_color("feedback.danger"),
                    text_color=theme_color("base.foreground")
                )
            except Exception:
                pass


class ScanOptionsPanel(CTkFrame):
    """
    Dynamic panel for scan mode options.

    Content swaps based on active scan mode:
    - Files: hash algo, min/max size, extensions
    - Photos: similarity threshold, format checkboxes
    - Videos: duration tolerance, frame count
    - Music: match fields checkboxes
    - Empty Folders: min depth
    - Large Files: top N count, min size
    """

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        subscribe_to_theme(self, self._apply_theme)

        self._current_mode: str = "files"
        self._option_widgets: Dict[str, tk.Widget] = {}

        # Callbacks
        self._on_options_changed: Optional[Callable[[Dict], None]] = None

        # Build UI
        self._build_ui()
        self._set_mode_options("files")

    def _build_ui(self) -> None:
        """Build options panel UI."""
        self.configure(
            fg_color=theme_color("base.backgroundTertiary")
        )

        # Title label
        CTkLabel(
            self,
            text="Scan Options",
            font=Typography.FONT_SM,
            text_color=theme_color("base.foregroundSecondary")
        ).pack(anchor="w", padx=Spacing.SM, pady=(Spacing.SM, 0))

        # Options container
        self._options_container = CTkFrame(self)
        self._options_container.pack(fill="both", expand=True, padx=Spacing.XS, pady=Spacing.SM)

    def _apply_theme(self) -> None:
        """Apply theme colors to all widgets."""
        try:
            self.configure(fg_color=theme_color("base.backgroundTertiary"))
        except Exception:
            pass
        # Rebuild mode options to pick up new colors
        self._set_mode_options(self._current_mode)

    def _set_mode_options(self, mode: str) -> None:
        """Swap options based on scan mode."""
        self._current_mode = mode

        # Clear existing options
        for widget in self._option_widgets.values():
            widget.destroy()
        self._option_widgets.clear()

        # Build mode-specific options
        if mode == "files":
            self._build_files_options()
        elif mode == "photos":
            self._build_photos_options()
        elif mode == "videos":
            self._build_videos_options()
        elif mode == "music":
            self._build_music_options()
        elif mode == "empty_folders":
            self._build_empty_folders_options()
        elif mode == "large_files":
            self._build_large_files_options()

    def _build_files_options(self) -> None:
        """Build file dedup options."""
        # Hash algorithm
        self._add_option_label("Hash Algorithm")
        self._add_option_menu(
            "Hash Algorithm",
            ["SHA256", "Blake3", "MD5"],
            "SHA256"
        )

        # Minimum size
        self._add_option_label("Minimum Size (MB)")
        self._add_slider(0, 1024, 0, "min_size")

        # Maximum size
        self._add_option_label("Maximum Size (MB)")
        self._add_slider(0, 10240, 0, "max_size")

    def _build_photos_options(self) -> None:
        """Build photo dedup options."""
        # Similarity threshold
        self._add_option_label("Similarity Threshold (Hamming Distance)")
        self._add_slider(1, 20, 10, "phash_threshold")

        # Format checkboxes
        self._add_option_label("Include Formats")
        self._add_checkbox("JPG/JPEG", True, "format_jpg")
        self._add_checkbox("PNG", True, "format_png")
        self._add_checkbox("WEBP", True, "format_webp")
        self._add_checkbox("HEIC", False, "format_heic")
        self._add_checkbox("RAW (CR2, NEF, DNG)", False, "format_raw")

    def _build_videos_options(self) -> None:
        """Build video dedup options."""
        # Duration tolerance
        self._add_option_label("Duration Tolerance (seconds)")
        self._add_slider(0, 30, 3, "duration_tolerance")

        # Frame count
        self._add_option_label("Keyframe Count")
        self._add_option_menu(
            "Keyframe Count",
            ["3 (Fast)", "5 (Thorough)"],
            "3 (Fast)"
        )

    def _build_music_options(self) -> None:
        """Build music dedup options."""
        # Match fields
        self._add_option_label("Match Fields")
        self._add_checkbox("Artist", True, "match_artist")
        self._add_checkbox("Title", True, "match_title")
        self._add_checkbox("Album", False, "match_album")
        self._add_checkbox("Duration", True, "match_duration")

        # Similarity threshold
        self._add_option_label("Similarity Threshold (%)")
        self._add_slider(50, 100, 85, "similarity_threshold")

    def _build_empty_folders_options(self) -> None:
        """Build empty folders options."""
        self._add_option_label("Minimum Depth")
        self._add_slider(0, 10, 0, "min_depth")

    def _build_large_files_options(self) -> None:
        """Build large files options."""
        self._add_option_label("Top N Files")
        self._add_slider(10, 500, 100, "top_n")

        self._add_option_label("Minimum Size (MB)")
        self._add_slider(0, 1024, 100, "min_size_mb")

        self._add_checkbox("Group by File Type", True, "group_by_type")

    def _add_option_label(self, text: str) -> None:
        """Add a label for an option."""
        CTkLabel(
            self._options_container,
            text=text,
            font=Typography.FONT_SM,
            text_color=theme_color("base.foregroundSecondary"),
            anchor="w"
        ).pack(fill="x", padx=Spacing.SM, pady=(Spacing.SM, 0))

    def _add_option_menu(
        self,
        name: str,
        values: List[str],
        default: str
    ) -> CTkOptionMenu:
        """Add an option menu."""
        menu = CTkOptionMenu(
            self._options_container,
            values=values,
            default_value=default,
            font=Typography.FONT_SM,
            fg_color=theme_color("base.foreground"),
            button_color=theme_color("base.backgroundElevated"),
            dropdown_fg_color=theme_color("base.foreground")
        )
        menu.pack(fill="x", padx=Spacing.SM, pady=(Spacing.XS, Spacing.SM))
        self._option_widgets[name] = menu
        return menu

    def _add_slider(
        self,
        min_val: float,
        max_val: float,
        default: float,
        name: str
    ) -> CTkSlider:
        """Add a slider option."""
        slider = CTkSlider(
            self._options_container,
            from_=min_val,
            to=max_val,
            number_of_steps=int(max_val - min_val),
            font=Typography.FONT_SM
        )
        slider.set(default)
        slider.pack(fill="x", padx=Spacing.SM, pady=(Spacing.XS, Spacing.SM))
        self._option_widgets[name] = slider
        return slider

    def _add_checkbox(
        self,
        text: str,
        default: bool,
        name: str
    ) -> CTkCheckBox:
        """Add a checkbox option."""
        checkbox = CTkCheckBox(
            self._options_container,
            text=text,
            font=Typography.FONT_SM,
            onvalue=True,
            offvalue=False
        )
        if default:
            checkbox.select()
        checkbox.pack(anchor="w", padx=Spacing.SM, pady=(Spacing.XS, Spacing.SM))
        self._option_widgets[name] = checkbox
        return checkbox

    def set_mode(self, mode: str) -> None:
        """Set active scan mode and update options."""
        self._set_mode_options(mode)

    def get_options(self) -> Dict:
        """Get current options as a dictionary."""
        # TODO: Read values from widgets and return as dict
        return {
            "mode": self._current_mode
        }

    def on_options_changed(self, callback: Callable[[Dict], None]) -> None:
        """Set callback for options changed."""
        self._on_options_changed = callback


class FolderPanel(CTkFrame):
    """
    Complete left panel with 3 collapsible sections.

    Features:
    - Scan Folders section with add/remove
    - Protect Folders section with warning accent
    - Scan Options section with mode-specific widgets
    - Collapsible sections
    """

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        subscribe_to_theme(self, self._apply_theme)

        # Widgets
        self._scan_folders_section: Optional[CollapsibleSection] = None
        self._protect_folders_section: Optional[CollapsibleSection] = None
        self._options_section: Optional[CollapsibleSection] = None
        self._scan_folders_list: Optional[ScanFolderList] = None
        self._protect_folders_list: Optional[ProtectFolderList] = None
        self._options_panel: Optional[ScanOptionsPanel] = None

        # Callbacks
        self._on_folders_changed: Optional[Callable[[List[Path]], None]] = None
        self._on_protected_changed: Optional[Callable[[List[Path]], None]] = None
        self._on_options_changed: Optional[Callable[[str, Dict], None]] = None

        # Build UI
        self._build_ui()

    def _build_ui(self) -> None:
        """Build folder panel UI."""
        self.configure(
            fg_color=theme_color("panel.background")
        )

        # Scan Folders section
        self._scan_folders_section = CollapsibleSection(
            self,
            title="Scan Folders",
            count=0
        )
        self._scan_folders_section.pack(fill="x", padx=Spacing.XS, pady=(Spacing.SM, 0))

        self._scan_folders_list = ScanFolderList(
            self._scan_folders_section.get_content_frame(),
            height=200
        )
        self._scan_folders_list.pack(fill="both", expand=True)
        self._scan_folders_list.on_folder_added(self._on_scan_folder_added)
        self._scan_folders_list.on_folder_removed(self._on_scan_folder_removed)

        # Protect Folders section
        self._protect_folders_section = CollapsibleSection(
            self,
            title="Protect Folders",
            count=0,
            accent_color=theme_color("feedback.warning")
        )
        self._protect_folders_section.pack(fill="x", padx=Spacing.XS, pady=Spacing.SM)

        self._protect_folders_list = ProtectFolderList(
            self._protect_folders_section.get_content_frame(),
            height=150
        )
        self._protect_folders_list.pack(fill="both", expand=True)
        self._protect_folders_list.on_folder_added(self._on_protected_folder_added)
        self._protect_folders_list.on_folder_removed(self._on_protected_folder_removed)

        # Scan Options section
        self._options_section = CollapsibleSection(
            self,
            title="Scan Options",
            count=0
        )
        self._options_section.pack(fill="x", padx=Spacing.XS, pady=Spacing.SM)

        self._options_panel = ScanOptionsPanel(
            self._options_section.get_content_frame()
        )
        self._options_panel.pack(fill="both", expand=True)

    def _apply_theme(self) -> None:
        """Apply theme colors to all widgets."""
        try:
            self.configure(fg_color=theme_color("panel.background"))
        except Exception:
            pass
        # Update protect section accent color on theme change
        if self._protect_folders_section:
            try:
                self._protect_folders_section._custom_accent = theme_color("feedback.warning")
                self._protect_folders_section._accent_color = theme_color("feedback.warning")
                self._protect_folders_section._apply_theme()
            except Exception:
                pass

    def _on_scan_folder_added(self, path: Path) -> None:
        """Handle scan folder added."""
        self._scan_folders_section.increment_count()
        if self._on_folders_changed:
            self._on_folders_changed(self._scan_folders_list.get_folders())

    def _on_scan_folder_removed(self, path: Path) -> None:
        """Handle scan folder removed."""
        self._scan_folders_section.decrement_count()
        if self._on_folders_changed:
            self._on_folders_changed(self._scan_folders_list.get_folders())

    def _on_protected_folder_added(self, path: Path) -> None:
        """Handle protected folder added."""
        self._protect_folders_section.increment_count()
        if self._on_protected_changed:
            self._on_protected_changed(self._protect_folders_list.get_folders())

    def _on_protected_folder_removed(self, path: Path) -> None:
        """Handle protected folder removed."""
        self._protect_folders_section.decrement_count()
        if self._on_protected_changed:
            self._on_protected_changed(self._protect_folders_list.get_folders())

    def set_scan_mode(self, mode: str) -> None:
        """Set active scan mode (updates options panel)."""
        self._options_panel.set_mode(mode)

    def get_scan_folders(self) -> List[Path]:
        """Get list of scan folders."""
        return self._scan_folders_list.get_folders()

    def get_protected_folders(self) -> List[Path]:
        """Get list of protected folders."""
        return self._protect_folders_list.get_folders()

    def get_options(self) -> Dict:
        """Get current scan options."""
        return self._options_panel.get_options()

    def set_scan_folders(self, folders: List[Path]) -> None:
        """Set scan folders list."""
        current_count = len(self._scan_folders_list.get_folders())
        self._scan_folders_list.set_folders(folders)
        new_count = len(folders)
        self._scan_folders_section.set_count(new_count)

    def set_protected_folders(self, folders: List[Path]) -> None:
        """Set protected folders list."""
        self._protect_folders_list.set_folders(folders)
        self._protect_folders_section.set_count(len(folders))

    def on_folders_changed(self, callback: Callable[[List[Path]], None]) -> None:
        """Set callback for scan folders changed."""
        self._on_folders_changed = callback

    def on_protected_changed(self, callback: Callable[[List[Path]], None]) -> None:
        """Set callback for protected folders changed."""
        self._on_protected_changed = callback

    def on_options_changed(self, callback: Callable[[str, Dict], None]) -> None:
        """Set callback for options changed."""
        self._on_options_changed = callback


# Simple logger fallback
logger = __import__('logging').getLogger(__name__)
