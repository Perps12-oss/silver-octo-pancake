# cerebro/ui/folder_panel.py
"""
Cerebro v2 Folder Panel Component

Left panel with tab-based layout:
1. Folders Tab - Scan folders list with add/remove and scan settings
2. Protect Tab - Protected folder list

Design: Tab-based navigation with scrollable content areas.
No text truncation or cut-off text.
Mode-dependent settings displayed in Folders tab.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

try:
    import customtkinter as ctk
except ImportError:
    ctk = None

from cerebro.core import DesignTokens


# ============================================================================
# Folder Row Component
# ============================================================================


class FolderRow:
    """
    Single folder row with remove button.

    Displays: [icon] [path] [remove]
    Full path displayed without truncation.
    """

    def __init__(
        self,
        parent: ctk.CTkFrame,
        path: str,
        on_remove: Callable[[str], None],
        is_protected: bool = False,
    ) -> None:
        """
        Initialize folder row.

        Args:
            parent: Parent frame
            path: Folder path to display
            on_remove: Callback when remove clicked
            is_protected: If True, use warning styling
        """
        self._frame = ctk.CTkFrame(
            master=parent,
            fg_color=DesignTokens.bg_tertiary,
        )
        self._on_remove = on_remove
        self._path = path

        # Style based on protected status
        bg_color = DesignTokens.bg_tertiary
        text_color = DesignTokens.text_primary
        accent_color = DesignTokens.accent

        if is_protected:
            bg_color = "#2A2510"  # Slightly darker for protected
            accent_color = DesignTokens.warning

        self._frame.configure(fg_color=bg_color)

        # Layout: [icon] [path] [remove button]
        self._frame.grid_columnconfigure(0, weight=0)  # Icon
        self._frame.grid_columnconfigure(1, weight=1)  # Path
        self._frame.grid_columnconfigure(2, weight=0)  # Remove

        # Icon
        icon = "📁" if not is_protected else "🔒"
        self._label_icon = ctk.CTkLabel(
            master=self._frame,
            text=icon,
            font=(DesignTokens.font_family_default, DesignTokens.font_size_default),
            text_color=DesignTokens.text_secondary,
        )
        self._label_icon.grid(row=0, column=0, padx=DesignTokens.spacing_md, pady=DesignTokens.spacing_sm)

        # Path label (full path, no truncation)
        self._label_path = ctk.CTkLabel(
            master=self._frame,
            text=path,
            anchor="w",
            font=(DesignTokens.font_family_default, DesignTokens.font_size_small),
            text_color=text_color,
            wraplength=0,  # No wrapping
        )
        self._label_path.grid(row=0, column=1, padx=DesignTokens.spacing_sm, pady=DesignTokens.spacing_sm, sticky="ew")

        # Remove button
        self._btn_remove = ctk.CTkButton(
            master=self._frame,
            text="×",
            width=25,
            height=25,
            fg_color=DesignTokens.bg_tertiary,
            text_color=accent_color,
            hover_color=DesignTokens.bg_input,
            font=(DesignTokens.font_family_default, DesignTokens.font_size_large),
        )
        self._btn_remove.configure(command=lambda: self._on_remove(path))
        self._btn_remove.grid(row=0, column=2, padx=DesignTokens.spacing_sm, pady=DesignTokens.spacing_sm)

    def get_frame(self) -> ctk.CTkFrame:
        """Return the row frame."""
        return self._frame


# ============================================================================
# Tab View Component
# ============================================================================


class TabView(ctk.CTkTabview):
    """
    Custom tab view with consistent styling.

    Two tabs: Folders and Protect.
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        width: int = 200,
        height: int = 400,
        **kwargs,
    ) -> None:
        """
        Initialize tab view.

        Args:
            master: Parent frame
            width: Width of the tab view
            height: Height of the tab view
            **kwargs: Additional CTkTabview arguments
        """
        # Configure tab styling
        super().__init__(
            master=master,
            width=width,
            height=height,
            segmented_button_fg_color=DesignTokens.bg_secondary,
            segmented_button_selected_color=DesignTokens.accent,
            segmented_button_selected_hover_color=DesignTokens.accent_hover,
            segmented_button_unselected_color=DesignTokens.bg_tertiary,
            segmented_button_unselected_hover_color=DesignTokens.bg_input,
            text_color=DesignTokens.text_primary,
            text_color_disabled=DesignTokens.text_disabled,
            **kwargs,
        )

        # Add tabs
        self.add("📁 Folders")
        self.add("🛡 Protect")

        # Configure tab content frames
        for tab in ["📁 Folders", "🛡 Protect"]:
            self.tab(tab).configure(fg_color=DesignTokens.bg_secondary)


# ============================================================================
# Settings Panel Component
# ============================================================================


class SettingsPanel:
    """
    Mode-dependent settings panel.

    Shows scan settings based on current mode (Files, Music, Videos).
    """

    def __init__(self, parent: ctk.CTkScrollableFrame) -> None:
        """
        Initialize settings panel.

        Args:
            parent: Parent scrollable frame
        """
        self._parent = parent
        self._container = ctk.CTkFrame(
            master=parent,
            fg_color=DesignTokens.bg_tertiary,
        )
        self._container.pack(fill="x", pady=(DesignTokens.spacing_md, 0))

        # Header
        header = ctk.CTkLabel(
            master=self._container,
            text="Scan Settings",
            anchor="w",
            font=(DesignTokens.font_family_default, DesignTokens.font_size_small, "bold"),
            text_color=DesignTokens.text_primary,
        )
        header.pack(fill="x", padx=DesignTokens.spacing_md, pady=(DesignTokens.spacing_md, DesignTokens.spacing_sm))

        # Settings container
        self._settings_container = ctk.CTkFrame(master=self._container, fg_color="transparent")
        self._settings_container.pack(fill="x", padx=DesignTokens.spacing_md, pady=(0, DesignTokens.spacing_md))

        # Current settings widgets
        self._widgets: Dict[str, ctk.CTkWidget] = {}
        self._on_changed: Optional[Callable[[Dict], None]] = None

    def set_mode(self, mode: str) -> None:
        """
        Set the scan mode and update settings display.

        Args:
            mode: One of "Files", "Music", "Videos"
        """
        # Clear existing widgets
        for widget in self._settings_container.winfo_children():
            widget.destroy()

        self._widgets.clear()

        if mode == "Files":
            self._create_files_settings()
        elif mode == "Music":
            self._create_music_settings()
        elif mode == "Videos":
            self._create_videos_settings()

    def _create_files_settings(self) -> None:
        """Create Files mode settings."""
        # Method
        self._create_dropdown(
            "Method",
            ["Exact Match", "Similarity"],
            "Exact Match",
            "method",
        )

        # Min Size
        self._create_entry(
            "Min Size (MB)",
            "0",
            "min_size",
        )

        # Skip Patterns
        self._create_entry(
            "Skip Patterns",
            "node_modules,.git",
            "skip_patterns",
        )

    def _create_music_settings(self) -> None:
        """Create Music mode settings."""
        # Method
        self._create_dropdown(
            "Method",
            ["Exact Match", "Similarity", "Metadata"],
            "Similarity",
            "method",
        )

        # Min Size
        self._create_entry(
            "Min Size (MB)",
            "0",
            "min_size",
        )

    def _create_videos_settings(self) -> None:
        """Create Videos mode settings."""
        # Method
        self._create_dropdown(
            "Method",
            ["Exact Match", "Similarity"],
            "Exact Match",
            "method",
        )

        # Min Size
        self._create_entry(
            "Min Size (MB)",
            "10",
            "min_size",
        )

    def _create_dropdown(
        self,
        label: str,
        values: List[str],
        default: str,
        key: str,
    ) -> None:
        """
        Create a dropdown setting.

        Args:
            label: Setting label
            values: Dropdown values
            default: Default value
            key: Setting key for callbacks
        """
        # Label
        lbl = ctk.CTkLabel(
            master=self._settings_container,
            text=label,
            anchor="w",
            font=(DesignTokens.font_family_default, DesignTokens.font_size_tiny),
            text_color=DesignTokens.text_secondary,
        )
        lbl.pack(fill="x", pady=(DesignTokens.spacing_sm, 0))

        # Dropdown
        dropdown = ctk.CTkOptionMenu(
            master=self._settings_container,
            values=values,
            default=default,
            fg_color=DesignTokens.bg_input,
            button_color=DesignTokens.bg_input,
            button_hover_color=DesignTokens.bg_tertiary,
            dropdown_fg_color=DesignTokens.bg_tertiary,
            dropdown_hover_color=DesignTokens.accent,
            text_color=DesignTokens.text_primary,
            font=(DesignTokens.font_family_default, DesignTokens.font_size_tiny),
            height=28,
        )

        def on_change(value: str) -> None:
            self._notify_changed(key, value)

        dropdown.configure(command=on_change)
        dropdown.pack(fill="x", pady=(DesignTokens.spacing_xs, DesignTokens.spacing_sm))
        self._widgets[key] = dropdown

    def _create_entry(
        self,
        label: str,
        default: str,
        key: str,
    ) -> None:
        """
        Create an entry setting.

        Args:
            label: Setting label
            default: Default value
            key: Setting key for callbacks
        """
        # Label
        lbl = ctk.CTkLabel(
            master=self._settings_container,
            text=label,
            anchor="w",
            font=(DesignTokens.font_family_default, DesignTokens.font_size_tiny),
            text_color=DesignTokens.text_secondary,
        )
        lbl.pack(fill="x", pady=(DesignTokens.spacing_sm, 0))

        # Entry
        entry = ctk.CTkEntry(
            master=self._settings_container,
            placeholder_text=default,
            fg_color=DesignTokens.bg_input,
            border_color=DesignTokens.border,
            text_color=DesignTokens.text_primary,
            placeholder_text_color=DesignTokens.text_secondary,
            font=(DesignTokens.font_family_default, DesignTokens.font_size_tiny),
            height=28,
        )

        def on_entry_change() -> None:
            self._notify_changed(key, entry.get())

        entry.bind("<KeyRelease>", lambda e: on_entry_change())
        entry.pack(fill="x", pady=(DesignTokens.spacing_xs, DesignTokens.spacing_sm))
        self._widgets[key] = entry

    def _notify_changed(self, key: str, value: str) -> None:
        """
        Notify callback of setting change.

        Args:
            key: Setting key
            value: New value
        """
        if self._on_changed:
            self._on_changed({key: value})

    def set_on_changed(self, callback: Callable[[Dict], None]) -> None:
        """
        Set callback for setting changes.

        Args:
            callback: Callback function receiving {key: value} dict
        """
        self._on_changed = callback

    def get_settings(self) -> Dict[str, str]:
        """
        Get current settings values.

        Returns:
            Dict of setting keys to values
        """
        settings = {}
        for key, widget in self._widgets.items():
            if isinstance(widget, ctk.CTkOptionMenu):
                settings[key] = widget.get()
            elif isinstance(widget, ctk.CTkEntry):
                settings[key] = widget.get()
        return settings


# ============================================================================
# Folder Panel Component
# ============================================================================


class FolderPanel:
    """
    Left panel with tab-based layout.

    Folders Tab:
    - Scan folder list with add/remove buttons
    - Scan settings (mode-dependent)

    Protect Tab:
    - Protected folder list
    """

    def __init__(self, parent: Optional[ctk.CTk] = None) -> None:
        """
        Initialize folder panel.

        Args:
            parent: Parent CTk widget
        """
        if ctk is None:
            raise ImportError("customtkinter is required for Cerebro v2 UI")

        self._parent = parent
        self._frame: Optional[ctk.CTkFrame] = None
        self._min_width = DesignTokens.min_left_panel_width

        # Data
        self._scan_folders: List[str] = []
        self._protected_folders: List[str] = []

        # Callbacks
        self._on_add_folder: Optional[Callable[[], None]] = None
        self._on_remove_scan_folder: Optional[Callable[[str], None]] = None
        self._on_remove_protected_folder: Optional[Callable[[str], None]] = None
        self._on_options_changed: Optional[Callable[[Dict], None]] = None

        # UI components
        self._tabview: Optional[TabView] = None
        self._folders_container: Optional[ctk.CTkFrame] = None
        self._protected_container: Optional[ctk.CTkFrame] = None
        self._settings_panel: Optional[SettingsPanel] = None

    def build(self) -> ctk.CTkFrame:
        """
        Build and return the folder panel frame.

        Returns:
            CTkFrame with tab-based layout.
        """
        self._frame = ctk.CTkFrame(
            master=self._parent,
            fg_color=DesignTokens.bg_secondary,
            width=self._min_width,
        )

        # Configure grid for full height
        self._frame.grid_rowconfigure(0, weight=1)
        self._frame.grid_columnconfigure(0, weight=1)

        # Create tab view
        self._tabview = TabView(
            master=self._frame,
            width=self._min_width,
        )
        self._tabview.grid(row=0, column=0, sticky="nsew")

        # Build Folders tab content
        self._build_folders_tab()

        # Build Protect tab content
        self._build_protect_tab()

        return self._frame

    def _build_folders_tab(self) -> None:
        """Build the Folders tab content."""
        tab_frame = self._tabview.tab("📁 Folders")

        # Main scrollable container
        scroll_frame = ctk.CTkScrollableFrame(
            master=tab_frame,
            fg_color=DesignTokens.bg_secondary,
            label_text="",
        )
        scroll_frame.pack(fill="both", expand=True)

        # Add "Add Path" button
        add_btn = ctk.CTkButton(
            master=scroll_frame,
            text="+ Add Path",
            height=30,
            fg_color=DesignTokens.accent,
            text_color=DesignTokens.text_on_accent,
            hover_color=DesignTokens.accent_hover,
            font=(DesignTokens.font_family_default, DesignTokens.font_size_small),
        )
        add_btn.pack(fill="x", padx=DesignTokens.spacing_md, pady=(DesignTokens.spacing_sm, DesignTokens.spacing_md))

        if self._on_add_folder is not None:
            add_btn.configure(command=self._on_add_folder)

        # Container for folder rows
        self._folders_container = ctk.CTkFrame(master=scroll_frame, fg_color="transparent")
        self._folders_container.pack(fill="x", padx=DesignTokens.spacing_md)

        # Refresh folder rows
        self._refresh_folders()

        # Separator
        separator = ctk.CTkFrame(master=scroll_frame, height=1, fg_color=DesignTokens.border_subtle)
        separator.pack(fill="x", padx=DesignTokens.spacing_md, pady=DesignTokens.spacing_md)

        # Create settings panel
        self._settings_panel = SettingsPanel(scroll_frame)

    def _build_protect_tab(self) -> None:
        """Build the Protect tab content."""
        tab_frame = self._tabview.tab("🛡 Protect")

        # Main scrollable container
        scroll_frame = ctk.CTkScrollableFrame(
            master=tab_frame,
            fg_color=DesignTokens.bg_secondary,
            label_text="",
        )
        scroll_frame.pack(fill="both", expand=True)

        # Add "Protect Folder" button
        add_btn = ctk.CTkButton(
            master=scroll_frame,
            text="+ Protect Folder",
            height=30,
            fg_color=DesignTokens.warning,
            text_color=DesignTokens.text_on_accent,
            hover_color="#D29922",
            font=(DesignTokens.font_family_default, DesignTokens.font_size_small),
        )
        add_btn.pack(fill="x", padx=DesignTokens.spacing_md, pady=(DesignTokens.spacing_sm, DesignTokens.spacing_md))

        if self._on_add_folder is not None:
            add_btn.configure(command=self._on_add_folder)

        # Container for protected folder rows
        self._protected_container = ctk.CTkFrame(master=scroll_frame, fg_color="transparent")
        self._protected_container.pack(fill="x", padx=DesignTokens.spacing_md)

        # Refresh protected folder rows
        self._refresh_protected_folders()

    # -------------------------------------------------------------------------
    # Folder Management
    # -------------------------------------------------------------------------

    def add_scan_folder(self, path: str) -> None:
        """
        Add a folder to the scan list.

        Args:
            path: Folder path to add
        """
        if path and path not in self._scan_folders:
            self._scan_folders.append(path)
            self._refresh_folders()

    def remove_scan_folder(self, path: str) -> None:
        """
        Remove a folder from the scan list.

        Args:
            path: Folder path to remove
        """
        if path in self._scan_folders:
            self._scan_folders.remove(path)
            self._refresh_folders()

    def add_protected_folder(self, path: str) -> None:
        """
        Add a folder to the protected list.

        Args:
            path: Folder path to protect
        """
        if path and path not in self._protected_folders:
            self._protected_folders.append(path)
            self._refresh_protected_folders()

    def remove_protected_folder(self, path: str) -> None:
        """
        Remove a folder from the protected list.

        Args:
            path: Folder path to remove
        """
        if path in self._protected_folders:
            self._protected_folders.remove(path)
            self._refresh_protected_folders()

    def clear_folders(self) -> None:
        """Clear all folders from scan list."""
        self._scan_folders.clear()
        self._refresh_folders()

    def clear_protected(self) -> None:
        """Clear all protected folders."""
        self._protected_folders.clear()
        self._refresh_protected_folders()

    def _refresh_folders(self) -> None:
        """Refresh the scan folders list display."""
        if not hasattr(self, "_folders_container") or self._folders_container is None:
            return

        # Clear existing
        for widget in self._folders_container.winfo_children():
            widget.destroy()

        # Add rows
        for path in self._scan_folders:
            row = FolderRow(
                parent=self._folders_container,
                path=path,
                on_remove=self._on_remove_scan_folder,
                is_protected=False,
            )
            row.get_frame().pack(fill="x", pady=(0, 1))

    def _refresh_protected_folders(self) -> None:
        """Refresh the protected folders list display."""
        if not hasattr(self, "_protected_container") or self._protected_container is None:
            return

        # Clear existing
        for widget in self._protected_container.winfo_children():
            widget.destroy()

        # Add rows
        for path in self._protected_folders:
            row = FolderRow(
                parent=self._protected_container,
                path=path,
                on_remove=self._on_remove_protected_folder,
                is_protected=True,
            )
            row.get_frame().pack(fill="x", pady=(0, 1))

    def set_scan_folders(self, folders: List[str]) -> None:
        """Set all scan folders at once."""
        self._scan_folders = list(folders)
        self._refresh_folders()

    def set_protected_folders(self, folders: List[str]) -> None:
        """Set all protected folders at once."""
        self._protected_folders = list(folders)
        self._refresh_protected_folders()

    def get_scan_folders(self) -> List[str]:
        """Return current scan folders list."""
        return list(self._scan_folders)

    def get_protected_folders(self) -> List[str]:
        """Return current protected folders list."""
        return list(self._protected_folders)

    # -------------------------------------------------------------------------
    # Callback Setters
    # -------------------------------------------------------------------------

    def set_on_add_folder(self, callback: Callable[[], None]) -> None:
        """Set callback for Add Path button."""
        self._on_add_folder = callback

    def set_on_remove_scan_folder(self, callback: Callable[[str], None]) -> None:
        """Set callback for removing scan folders."""
        self._on_remove_scan_folder = callback

    def set_on_remove_protected_folder(self, callback: Callable[[str], None]) -> None:
        """Set callback for removing protected folders."""
        self._on_remove_protected_folder = callback

    def set_on_options_changed(self, callback: Callable[[Dict], None]) -> None:
        """Set callback for options changes."""
        self._on_options_changed = callback
        if self._settings_panel:
            self._settings_panel.set_on_changed(callback)

    # -------------------------------------------------------------------------
    # Mode and Options
    # -------------------------------------------------------------------------

    def set_mode(self, mode: str) -> None:
        """
        Set the scan mode and update settings panel.

        Args:
            mode: One of "Files", "Music", "Videos"
        """
        if self._settings_panel:
            self._settings_panel.set_mode(mode)

    def set_options_content(self, widgets: List[ctk.CTkWidget]) -> None:
        """
        Set the scan options content for the current mode.

        Note: This is maintained for backwards compatibility.
        Mode-dependent settings are now managed by set_mode().

        Args:
            widgets: List of widgets to display (ignored in new implementation)
        """
        # Settings are now managed by SettingsPanel
        pass

    def clear_options(self) -> None:
        """Clear all option widgets."""
        # Settings are now managed by SettingsPanel
        if self._settings_panel:
            self._settings_panel.set_mode("Files")

    def get_frame(self) -> Optional[ctk.CTkFrame]:
        """Return the folder panel frame."""
        return self._frame


__all__ = [
    "FolderPanel",
    "FolderRow",
    "TabView",
    "SettingsPanel",
]
