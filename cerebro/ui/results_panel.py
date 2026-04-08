# cerebro/ui/results_panel.py
"""
Cerebro v2 Results Panel Component

Center panel for displaying grouped duplicate results.
Features:
    - Grouped duplicates with collapsible parent rows
    - Checkboxes on each file row
    - Sortable columns (Name, Extension, Size, Modified, Similarity, Path)
    - Right-click context menu
    - Sub-filter tabs (All | Images | Videos | Docs | Audio | Other)

Design: Uses CheckTreeview (from ui/widgets) for display.
Groups are shown as colored parent rows with expand/collapse.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

try:
    import customtkinter as ctk
except ImportError:
    ctk = None

from cerebro.core import DesignTokens
from cerebro.ui.widgets.check_treeview import CheckTreeview


# ============================================================================
# Result Data
# ============================================================================


@dataclass
class DuplicateResult:
    """A single duplicate group for the results panel."""

    group_id: int
    files: List[dict]
    total_size: int
    reclaimable: int
    similarity_score: float = 1.0

    @property
    def file_count(self) -> int:
        """Number of files in this group."""
        return len(self.files)

    @property
    def checked_count(self) -> int:
        """Number of files marked for deletion."""
        return sum(1 for f in self.files if f.get("checked", False))

    @property
    def reclaimable_human(self) -> str:
        """Reclaimable space in human-readable format."""
        return self._format_bytes(self.reclaimable)

    @property
    def total_size_human(self) -> str:
        """Total size in human-readable format."""
        return self._format_bytes(self.total_size)

    @staticmethod
    def _format_bytes(size: int) -> str:
        """Format bytes as human-readable."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"


# ============================================================================
# Results Panel Component
# ============================================================================


class ResultsPanel:
    """
    Center panel for displaying grouped duplicate results.

    Displays:
        - Grouped duplicates as a tree structure
        - Checkboxes for selecting files to delete
        - Sortable columns
        - Context menu (right-click)
        - Sub-filter tabs (file type filtering)
    """

    # Filter types
    FILTER_ALL = "all"
    FILTER_IMAGES = "images"
    FILTER_VIDEOS = "videos"
    FILTER_DOCS = "docs"
    FILTER_AUDIO = "audio"
    FILTER_OTHER = "other"

    FILTER_NAMES = {
        FILTER_ALL: "All",
        FILTER_IMAGES: "Images",
        FILTER_VIDEOS: "Videos",
        FILTER_DOCS: "Documents",
        FILTER_AUDIO: "Audio",
        FILTER_OTHER: "Other",
    }

    # Panel states
    STATE_EMPTY = "empty"
    STATE_SCANNING = "scanning"
    STATE_RESULTS = "results"

    def __init__(self, parent: Optional[ctk.CTk] = None) -> None:
        """
        Initialize results panel.

        Args:
            parent: Parent CTk widget
        """
        if ctk is None:
            raise ImportError("customtkinter is required for Cerebro v2 UI")

        self._parent = parent
        self._frame: Optional[ctk.CTkFrame] = None

        # Data
        self._groups: List[DuplicateResult] = []
        self._selected_count = 0
        self._total_files = 0

        # Current filter
        self._current_filter = self.FILTER_ALL

        # Panel state
        self._state = self.STATE_EMPTY

        # Callbacks
        self._on_file_selected: Optional[Callable[[str, dict], None]] = None
        self._on_group_toggle: Optional[Callable[[int], None]] = None
        self._on_delete_selected: Optional[Callable[[], None]] = None
        self._on_refresh: Optional[Callable[[], None]] = None

        # Widgets
        self._filter_tabs: Optional[ctk.CTkSegmentedButton] = None
        self._tree: Optional[CheckTreeview] = None
        self._group_rows: Dict[int, ctk.CTkFrame] = {}

        # State widgets (empty/scanning views)
        self._empty_frame: Optional[ctk.CTkFrame] = None
        self._scanning_frame: Optional[ctk.CTkFrame] = None
        self._progress_bar: Optional[ctk.CTkProgressBar] = None
        self._label_progress: Optional[ctk.CTkLabel] = None
        self._label_current_file: Optional[ctk.CTkLabel] = None

        # Group to files mapping for treeview
        self._group_file_ids: Dict[int, List[str]] = {}

        # Sort column and direction
        self._sort_column = "size"
        self._sort_ascending = False

    def build(self) -> ctk.CTkFrame:
        """
        Build and return the results panel frame.

        Returns:
            CTkFrame containing filter tabs, treeview, and context menu.
        """
        self._frame = ctk.CTkFrame(
            master=self._parent,
            fg_color=DesignTokens.bg_primary,
        )

        # Layout: filter tabs on top, content below
        self._frame.grid_columnconfigure(0, weight=1)
        self._frame.grid_rowconfigure(0, weight=0)  # Filter tabs
        self._frame.grid_rowconfigure(1, weight=1)  # Content (empty/scanning/tree)

        self._create_filter_tabs()
        self._create_empty_state()
        self._create_scanning_state()
        self._create_treeview()

        # Show empty state initially
        self._set_state(self.STATE_EMPTY)

        return self._frame

    def _create_filter_tabs(self) -> None:
        """Create file type filter tabs."""
        # Create with initial labels (will be updated with counts when groups are set)
        filter_values = list(self.FILTER_NAMES.values())
        self._filter_tabs = ctk.CTkSegmentedButton(
            master=self._frame,
            values=filter_values,
            font=(DesignTokens.font_family_default, DesignTokens.font_size_small),
        )
        self._filter_tabs.set(self.FILTER_NAMES[self.FILTER_ALL])

        # Apply styling
        self._filter_tabs.configure(
            selected_color=DesignTokens.accent,
            selected_hover_color=DesignTokens.accent_hover,
            unselected_color=DesignTokens.bg_tertiary,
            unselected_hover_color=DesignTokens.bg_input,
            text_color=DesignTokens.text_primary,
        )

        # Wire callback
        if self._on_refresh is not None:
            self._filter_tabs.configure(command=lambda: self._set_filter(self._filter_tabs.get()))

        # Note: Filter tabs are not gridded initially - visibility controlled by _set_state()

    def _create_treeview(self) -> None:
        """Create the results treeview using CheckTreeview widget."""
        # Use CheckTreeview widget for displaying grouped duplicates
        import tkinter as tk

        self._tree = CheckTreeview(
            parent=self._frame,
            on_file_checked=self._on_file_checked_callback,
            on_file_double_click=self._on_file_double_click_callback,
        )

        # Grid the treeview (will be shown/hidden based on state)
        self._tree.grid(row=1, column=0, sticky="nsew", padx=DesignTokens.spacing_sm, pady=DesignTokens.spacing_sm)

    def _create_empty_state(self) -> None:
        """Create the empty state view shown before scan."""
        self._empty_frame = ctk.CTkFrame(
            master=self._frame,
            fg_color=DesignTokens.bg_secondary,
        )

        # Center content
        self._empty_frame.grid_columnconfigure(0, weight=1)
        self._empty_frame.grid_rowconfigure(0, weight=1)

        # Icon/emoji
        icon_label = ctk.CTkLabel(
            master=self._empty_frame,
            text="📁",
            font=(DesignTokens.font_family_default, 64),
        )
        icon_label.grid(row=0, column=0, pady=(DesignTokens.spacing_xl, DesignTokens.spacing_sm))

        # Empty state message
        message_label = ctk.CTkLabel(
            master=self._empty_frame,
            text="Add folders and click Search Now",
            font=(DesignTokens.font_family_default, DesignTokens.font_size_default),
            text_color=DesignTokens.text_primary,
        )
        message_label.grid(row=1, column=0, pady=DesignTokens.spacing_md)

        # Subtitle
        subtitle_label = ctk.CTkLabel(
            master=self._empty_frame,
            text="Scan folders to find duplicate files",
            font=(DesignTokens.font_family_default, DesignTokens.font_size_small),
            text_color=DesignTokens.text_secondary,
        )
        subtitle_label.grid(row=2, column=0, pady=(0, DesignTokens.spacing_xl))

        # Grid the empty frame (will be shown/hidden based on state)
        self._empty_frame.grid(row=1, column=0, sticky="nsew")

    def _create_scanning_state(self) -> None:
        """Create the scanning state view shown during scan."""
        self._scanning_frame = ctk.CTkFrame(
            master=self._frame,
            fg_color=DesignTokens.bg_secondary,
        )

        # Center content
        self._scanning_frame.grid_columnconfigure(0, weight=1)
        self._scanning_frame.grid_rowconfigure((0, 1, 2), weight=0)

        # Scanning icon
        icon_label = ctk.CTkLabel(
            master=self._scanning_frame,
            text="🔍",
            font=(DesignTokens.font_family_default, 64),
        )
        icon_label.grid(row=0, column=0, pady=(DesignTokens.spacing_xl, DesignTokens.spacing_md))

        # Scanning message
        message_label = ctk.CTkLabel(
            master=self._scanning_frame,
            text="Scanning...",
            font=(DesignTokens.font_family_default, DesignTokens.font_size_default),
            text_color=DesignTokens.text_primary,
        )
        message_label.grid(row=1, column=0, pady=DesignTokens.spacing_sm)

        # Progress bar
        self._progress_bar = ctk.CTkProgressBar(
            master=self._scanning_frame,
            width=300,
            height=20,
            progress_color=DesignTokens.accent,
        )
        self._progress_bar.set(0.5)  # Start at middle for pulsing effect
        self._progress_bar.grid(row=2, column=0, pady=DesignTokens.spacing_md)

        # Current file label
        self._label_current_file = ctk.CTkLabel(
            master=self._scanning_frame,
            text="",
            font=(DesignTokens.font_family_default, DesignTokens.font_size_small),
            text_color=DesignTokens.text_secondary,
        )
        self._label_current_file.grid(row=3, column=0, pady=(0, DesignTokens.spacing_xl))

        # Grid the scanning frame (will be shown/hidden based on state)
        self._scanning_frame.grid(row=1, column=0, sticky="nsew")

    def _set_state(self, state: str) -> None:
        """
        Set the panel state and show/hide appropriate widgets.

        Args:
            state: One of STATE_EMPTY, STATE_SCANNING, STATE_RESULTS
        """
        self._state = state

        # Hide all state frames and treeview
        if self._empty_frame:
            self._empty_frame.grid_forget()
        if self._scanning_frame:
            self._scanning_frame.grid_forget()
        if self._tree:
            self._tree.grid_forget()

        # Hide filter tabs in empty and scanning states
        if self._filter_tabs:
            if state == self.STATE_RESULTS:
                self._filter_tabs.grid(row=0, column=0, sticky="ew", padx=DesignTokens.spacing_md, pady=(DesignTokens.spacing_sm, 0))
            else:
                self._filter_tabs.grid_forget()

        # Show appropriate state
        if state == self.STATE_EMPTY:
            if self._empty_frame:
                self._empty_frame.grid(row=1, column=0, sticky="nsew")
        elif state == self.STATE_SCANNING:
            if self._scanning_frame:
                self._scanning_frame.grid(row=1, column=0, sticky="nsew")
        elif state == self.STATE_RESULTS:
            if self._tree:
                self._tree.grid(row=1, column=0, sticky="nsew")

    def _set_filter(self, filter_type: str) -> None:
        """
        Set the current file type filter.

        Args:
            filter_type: Display label (e.g., "All (347)" or "All")
        """
        # Extract the filter type name from the display label (before any count)
        display_name = filter_type.split(" (")[0]

        # Map display name back to filter type constant
        for filter_const, name in self.FILTER_NAMES.items():
            if name == display_name:
                self._current_filter = filter_const
                break

        # Refresh treeview (placeholder for now)
        # self._refresh_treeview()

    def _get_file_type_counts(self) -> dict:
        """
        Calculate file counts by type from current groups.

        Returns:
            Dictionary with counts for all, images, videos, audio, docs, other
        """
        counts = {
            self.FILTER_ALL: 0,
            self.FILTER_IMAGES: 0,
            self.FILTER_VIDEOS: 0,
            self.FILTER_AUDIO: 0,
            self.FILTER_DOCS: 0,
            self.FILTER_OTHER: 0,
        }

        # File type extensions (matching scan_result_store.py categories)
        image_exts = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".heic", ".heif", ".ico", ".svg"}
        video_exts = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".webm", ".flv", ".m4v", ".mpg", ".mpeg", ".3gp"}
        audio_exts = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".opus", ".aiff"}
        doc_exts = {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"}

        for group in self._groups:
            for file_data in group.files:
                path = file_data.get("path", "")
                ext = Path(path).suffix.lower()

                counts[self.FILTER_ALL] += 1

                if ext in image_exts:
                    counts[self.FILTER_IMAGES] += 1
                elif ext in video_exts:
                    counts[self.FILTER_VIDEOS] += 1
                elif ext in audio_exts:
                    counts[self.FILTER_AUDIO] += 1
                elif ext in doc_exts:
                    counts[self.FILTER_DOCS] += 1
                else:
                    counts[self.FILTER_OTHER] += 1

        return counts

    def _update_filter_tabs(self) -> None:
        """Update filter tab labels with current counts."""
        if self._filter_tabs is None:
            return

        counts = self._get_file_type_counts()

        # Build tab labels with counts
        labels = [
            f"{self.FILTER_NAMES[self.FILTER_ALL]} ({counts[self.FILTER_ALL]})",
            f"{self.FILTER_NAMES[self.FILTER_IMAGES]} ({counts[self.FILTER_IMAGES]})",
            f"{self.FILTER_NAMES[self.FILTER_VIDEOS]} ({counts[self.FILTER_VIDEOS]})",
            f"{self.FILTER_NAMES[self.FILTER_AUDIO]} ({counts[self.FILTER_AUDIO]})",
            f"{self.FILTER_NAMES[self.FILTER_DOCS]} ({counts[self.FILTER_DOCS]})",
            f"{self.FILTER_NAMES[self.FILTER_OTHER]} ({counts[self.FILTER_OTHER]})",
        ]

        # Configure the segmented button with new values
        self._filter_tabs.configure(values=labels)

        # Set the current selection based on the display name
        display_name = self.FILTER_NAMES.get(self._current_filter, self.FILTER_NAMES[self.FILTER_ALL])
        # Find the label that starts with our display name (before the count)
        current_label = next((l for l in labels if l.startswith(display_name)), labels[0])
        self._filter_tabs.set(current_label)

    def _refresh_treeview(self) -> None:
        """Refresh the treeview display."""
        if self._tree is None:
            return

        # Clear existing data
        self._tree.clear()
        self._group_file_ids.clear()

        # Add groups and files
        for group in self._groups:
            # Format size for display
            size_mb = group.reclaimable / (1024 * 1024)
            size_str = f"{size_mb:.1f} MB"

            # Add group header
            self._tree.add_group(
                group_id=group.group_id,
                name=group.total_size_human,
                file_count=group.file_count,
                reclaimable_mb=size_mb,
            )

            # Track file IDs for this group
            file_ids = []

            # Add files
            for file_data in group.files:
                file_id = file_data.get("id", f"{group.group_id}_{file_data.get('path', '')}")
                file_ids.append(file_id)

                # Format size
                size = file_data.get("size", 0)
                if size > 0:
                    size_str = f"{size / (1024 * 1024):.2f} MB"
                else:
                    size_str = "0 B"

                # Format modified date
                modified = file_data.get("modified", "")
                if isinstance(modified, (int, float)):
                    from datetime import datetime
                    modified = datetime.fromtimestamp(modified).strftime("%Y-%m-%d %H:%M")

                # Format similarity
                similarity = file_data.get("similarity", 100)
                if isinstance(similarity, float):
                    similarity_str = f"{similarity:.0f}%"
                else:
                    similarity_str = str(similarity) if similarity else "100%"

                self._tree.add_file(
                    group_id=group.group_id,
                    file_id=file_id,
                    name=file_data.get("name", ""),
                    size=size_str,
                    modified=modified,
                    similarity=similarity_str,
                    path=file_data.get("path", ""),
                    checked=file_data.get("checked", False),
                )

            self._group_file_ids[group.group_id] = file_ids

    def _toggle_group(self, group_id: int) -> None:
        """Toggle expand/collapse of a group."""
        if self._tree is None:
            return

        self._tree.toggle_group(group_id)

        # Call callback
        if self._on_group_toggle is not None:
            self._on_group_toggle(group_id)

    def _on_file_checked_callback(self, group_id: int, file_id: str, checked: bool) -> None:
        """Callback when file checkbox state changes."""
        # Find and update the file in our groups data
        for group in self._groups:
            for file_data in group.files:
                if file_data.get("id") == file_id:
                    file_data["checked"] = checked
                    file_data["is_keeper"] = not checked
                    break

        self._update_totals()

        # Call callback if set
        if self._on_file_selected is not None:
            file_data = self._find_file_data(file_id)
            if file_data:
                self._on_file_selected(group_id, file_data)

    def _on_file_double_click_callback(self, group_id: int, file_id: str) -> None:
        """Callback when file is double-clicked."""
        # Call callback if set
        if self._on_file_selected is not None:
            file_data = self._find_file_data(file_id)
            if file_data:
                self._on_file_selected(group_id, file_data)

    def _find_file_data(self, file_id: str) -> Optional[Dict]:
        """Find file data by ID."""
        for group in self._groups:
            for file_data in group.files:
                if file_data.get("id") == file_id:
                    return file_data
        return None

    # -------------------------------------------------------------------------
    # Data Management
    # -------------------------------------------------------------------------

    def set_groups(self, groups: List[DuplicateResult]) -> None:
        """
        Set the duplicate groups to display.

        Args:
            groups: List of duplicate groups to display
        """
        self._groups = groups
        self._update_totals()

        # Update filter tabs with counts
        self._update_filter_tabs()

        # Switch to results state
        self._set_state(self.STATE_RESULTS)

        # Refresh treeview
        self._refresh_treeview()

    def clear_groups(self) -> None:
        """Clear all groups and show empty state."""
        self._groups.clear()
        self._selected_count = 0
        self._total_files = 0
        self._group_file_ids.clear()

        # Switch to empty state
        self._set_state(self.STATE_EMPTY)

        # Clear treeview
        if self._tree is not None:
            self._tree.clear()

    def set_scanning(self, is_scanning: bool) -> None:
        """
        Set the scanning state.

        Args:
            is_scanning: True to show scanning state, False to return to previous state
        """
        if is_scanning:
            self._set_state(self.STATE_SCANNING)
        else:
            # Return to appropriate state based on whether we have results
            if self._groups:
                self._set_state(self.STATE_RESULTS)
            else:
                self._set_state(self.STATE_EMPTY)

    def update_scan_progress(
        self,
        files_scanned: int = 0,
        files_total: int = 0,
        duplicates_found: int = 0,
        current_file: str = "",
    ) -> None:
        """
        Update the scanning progress display.

        Args:
            files_scanned: Number of files processed
            files_total: Total files to process
            duplicates_found: Number of duplicates found
            current_file: Current file being scanned
        """
        if self._state != self.STATE_SCANNING:
            self._set_state(self.STATE_SCANNING)

        # Update progress bar (pulsing effect or actual progress)
        if self._progress_bar:
            if files_total > 0:
                progress = files_scanned / files_total
            else:
                # Pulse effect if total unknown
                import time
                progress = (time.time() % 2) / 2  # Oscillate 0-1 over 2 seconds
            self._progress_bar.set(progress)

        # Update current file label
        if self._label_current_file:
            if current_file:
                display = current_file
                if len(display) > 50:
                    display = "..." + display[-50:]
                self._label_current_file.configure(text=f"Scanning: {display}")
            else:
                self._label_current_file.configure(text=f"Files scanned: {files_scanned:,}")

        # Update progress label if exists
        if self._label_progress:
            self._label_progress.configure(text=f"Scanned {files_scanned:,} files")

    def _update_totals(self) -> None:
        """Update total counts."""
        self._total_files = sum(g.file_count for g in self._groups)
        self._selected_count = sum(g.checked_count for g in self._groups)

    # -------------------------------------------------------------------------
    # Selection
    # -------------------------------------------------------------------------

    def set_file_checked(self, group_id: int, file_id: str, checked: bool) -> None:
        """
        Set the checked state of a file.

        Args:
            group_id: ID of the group containing the file
            file_id: Unique ID for the file
            checked: True if file should be deleted, False if keeping
        """
        # Update internal data
        group = next((g for g in self._groups if g.group_id == group_id), None)
        if group:
            for file_data in group.files:
                if file_data.get("id") == file_id:
                    file_data["checked"] = checked
                    file_data["is_keeper"] = not checked
                    break

        self._update_totals()

        # Update treeview checkbox
        if self._tree is not None:
            self._tree.set_file_checked(file_id, checked)

        # Call callback
        if self._on_file_selected is not None:
            file_data = self._find_file_data(file_id)
            if file_data:
                self._on_file_selected(group_id, file_data)

    def toggle_all_files(self, checked: bool) -> None:
        """
        Toggle all files checked state.

        Args:
            checked: True to select all, False to deselect all
        """
        # Update internal data
        for group in self._groups:
            for file_data in group.files:
                file_data["checked"] = checked
                file_data["is_keeper"] = not checked

        self._update_totals()

        # Update treeview checkboxes
        if self._tree is not None:
            for group in self._groups:
                self._tree.select_group_files(group.group_id, checked)

    def delete_selected(self) -> None:
        """
        Delete all selected files and return them for actual deletion.

        Returns:
            List of selected file data dictionaries
        """
        selected_files = []

        for group in self._groups:
            for file_data in group.files:
                if file_data.get("checked", False):
                    selected_files.append(file_data)

        # Remove selected from groups (internal data)
        for file in selected_files:
            group_id = file.get("group_id", "")
            # Find group by matching file_id in group files
            for group in self._groups:
                if group.group_id == group_id:
                    file_id = file.get("id", "")
                    group.files = [f for f in group.files if f.get("id") != file_id]
                    break

        # Update totals
        self._update_totals()

        # Refresh treeview to reflect changes
        if self._tree is not None:
            self._refresh_treeview()

        # Call callback
        if self._on_delete_selected is not None:
            self._on_delete_selected(selected_files)

    # -------------------------------------------------------------------------
    # Sorting
    # -------------------------------------------------------------------------

    def sort_by_column(self, column: str, ascending: bool = True) -> None:
        """
        Sort groups by a column.

        Args:
            column: Column name (name, size, modified, similarity, path)
            ascending: Sort order (True = ascending, False = descending)
        """
        self._sort_column = column
        self._sort_ascending = ascending

        # Sort groups
        reverse = not ascending
        if column == "name":
            self._groups.sort(key=lambda g: self._files[0].get("path", "").name if reverse else self._files[-1].get("path", "").name, reverse=reverse)
        elif column == "size":
            self._groups.sort(key=lambda g: g.total_size, reverse=reverse)
        elif column == "modified":
            self._groups.sort(key=lambda g: self._files[0].get("modified", 0), reverse=reverse)
        elif column == "similarity":
            self._groups.sort(key=lambda g: g.similarity_score, reverse=reverse)
        elif column == "path":
            self._groups.sort(key=lambda g: self._files[0].get("path", ""), reverse=reverse)
        else:
            self._groups.sort(key=lambda g: g.group_id, reverse=reverse)

    # -------------------------------------------------------------------------
    # Callback Setters
    # -------------------------------------------------------------------------

    def set_on_file_selected(self, callback: Callable[[str, dict], None]) -> None:
        """Set callback for file selection changes."""
        self._on_file_selected = callback

    def set_on_group_toggle(self, callback: Callable[[int], None]) -> None:
        """Set callback for group expand/collapse."""
        self._on_group_toggle = callback

    def set_on_delete_selected(self, callback: Callable[[List[dict]], None]) -> None:
        """Set callback for delete action."""
        self._on_delete_selected = callback

    def set_on_refresh(self, callback: Callable[[], None]) -> None:
        """Set callback for refresh action."""
        self._on_refresh = callback

    # -------------------------------------------------------------------------
    # State Queries
    # -------------------------------------------------------------------------

    def get_frame(self) -> Optional[ctk.CTkFrame]:
        """Return the results panel frame."""
        return self._frame

    def get_groups(self) -> List[DuplicateResult]:
        """Return all groups."""
        return self._groups

    def get_selected_count(self) -> int:
        """Return number of selected files."""
        return self._selected_count

    def get_total_files(self) -> int:
        """Return total number of files."""
        return self._total_files


__all__ = [
    "ResultsPanel",
    "DuplicateResult",
]
