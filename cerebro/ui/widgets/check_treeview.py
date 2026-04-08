# cerebro/ui/widgets/check_treeview.py
"""
CheckTreeview Widget

A ttk.Treeview-based widget with checkbox support for displaying grouped duplicate files.
Features:
    - Parent/child grouping with collapsible group headers
    - Checkboxes that toggle on row click
    - Sortable columns
    - Alternating row colors within groups
    - Right-click context menu
    - Group header summaries showing file count and reclaimable space
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import tkinter as tk
from tkinter import ttk
import subprocess
import platform


# ============================================================================
# CheckTreeview Widget
# ============================================================================


class CheckTreeview(ttk.Frame):
    """
    A treeview widget with checkbox support for displaying grouped duplicate files.

    Features:
        - Checkbox column that toggles on row click
        - Parent/child grouping with expandable group headers
        - Sortable columns (click headers to sort)
        - Alternating row colors within groups
        - Group headers show: "Group N — X files, Y MB reclaimable"
        - Right-click context menu: Open File, Open Folder, Copy Path, Select Group

    Example:
        >>> tree = CheckTreeview(parent)
        >>> tree.pack(fill=tk.BOTH, expand=True)
        >>> tree.add_group(group_id=1, name="Duplicates", file_count=5, reclaimable_mb=102.4)
        >>> tree.add_file(group_id=1, file_id="f1", name="photo.jpg", size="2.5 MB",
        ...              modified="2024-01-15", similarity="95%", path="/path/to/photo.jpg")
    """

    # Column identifiers
    COL_CHECKBOX = "checkbox"
    COL_NAME = "name"
    COL_SIZE = "size"
    COL_MODIFIED = "modified"
    COL_SIMILARITY = "similarity"
    COL_PATH = "path"

    # Column display names
    COLUMN_NAMES = {
        COL_CHECKBOX: "",
        COL_NAME: "Name",
        COL_SIZE: "Size",
        COL_MODIFIED: "Modified",
        COL_SIMILARITY: "Similarity",
        COL_PATH: "Path",
    }

    # Column widths
    COLUMN_WIDTHS = {
        COL_CHECKBOX: 40,
        COL_NAME: 200,
        COL_SIZE: 100,
        COL_MODIFIED: 150,
        COL_SIMILARITY: 100,
        COL_PATH: 300,
    }

    def __init__(
        self,
        parent: tk.Misc,
        on_file_checked: Optional[Callable[[int, str, bool], None]] = None,
        on_file_double_click: Optional[Callable[[int, str], None]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the CheckTreeview widget.

        Args:
            parent: Parent widget
            on_file_checked: Callback when file checkbox state changes.
                Arguments: (group_id, file_id, checked_state)
            on_file_double_click: Callback when file is double-clicked.
                Arguments: (group_id, file_id)
            **kwargs: Additional arguments passed to ttk.Frame
        """
        super().__init__(parent, **kwargs)

        # Callbacks
        self._on_file_checked = on_file_checked
        self._on_file_double_click = on_file_double_click

        # Data storage
        self._group_data: Dict[int, Dict[str, Any]] = {}
        self._file_data: Dict[str, Dict[str, Any]] = {}
        self._file_to_group: Dict[str, int] = {}
        self._group_counter = 0

        # Sort state
        self._sort_column = self.COL_SIZE
        self._sort_ascending = False

        # Build UI
        self._create_widgets()
        self._setup_bindings()

    def _create_widgets(self) -> None:
        """Create the treeview and scrollbar widgets."""
        # Create treeview
        self._tree = ttk.Treeview(
            self,
            columns=list(self.COLUMN_NAMES.keys()),
            show="tree headings",
            selectmode="browse",
        )

        # Configure columns
        for col, name in self.COLUMN_NAMES.items():
            self._tree.heading(col, text=name, command=lambda c=col: self._on_column_click(c))
            self._tree.column(col, width=self.COLUMN_WIDTHS.get(col, 100), stretch=tk.YES)

        # Create vertical scrollbar
        self._vscrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=self._vscrollbar.set)

        # Create horizontal scrollbar
        self._hscrollbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self._tree.xview)
        self._tree.configure(xscrollcommand=self._hscrollbar.set)

        # Grid layout
        self._tree.grid(row=0, column=0, sticky="nsew")
        self._vscrollbar.grid(row=0, column=1, sticky="ns")
        self._hscrollbar.grid(row=1, column=0, sticky="ew")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def _setup_bindings(self) -> None:
        """Setup event bindings."""
        self._tree.bind("<Button-1>", self._on_tree_click)
        self._tree.bind("<Double-1>", self._on_tree_double_click)
        self._tree.bind("<Button-3>", self._on_context_menu)  # Right-click on Windows/Linux
        self._tree.bind("<Button-2>", self._on_context_menu)  # Right-click on macOS

    # -------------------------------------------------------------------------
    # Group Management
    # -------------------------------------------------------------------------

    def add_group(
        self,
        group_id: int,
        name: str,
        file_count: int,
        reclaimable_mb: float,
    ) -> str:
        """
        Add a group header to the treeview.

        Args:
            group_id: Unique identifier for the group
            name: Group name/description
            file_count: Number of files in the group
            reclaimable_mb: Reclaimable space in MB

        Returns:
            The treeview item ID for the group
        """
        self._group_counter += 1
        item_id = f"group_{group_id}"

        # Format the header
        header_text = f"Group {group_id} — {file_count} files, {reclaimable_mb:.1f} MB reclaimable"

        # Insert the group
        self._tree.insert(
            "",
            tk.END,
            iid=item_id,
            text=header_text,
            tags=("group",),
        )

        # Store group data
        self._group_data[group_id] = {
            "name": name,
            "file_count": file_count,
            "reclaimable_mb": reclaimable_mb,
            "item_id": item_id,
            "expanded": True,
        }

        return item_id

    def expand_group(self, group_id: int) -> None:
        """Expand a group to show its files."""
        if group_id in self._group_data:
            item_id = self._group_data[group_id]["item_id"]
            self._tree.item(item_id, open=True)
            self._group_data[group_id]["expanded"] = True

    def collapse_group(self, group_id: int) -> None:
        """Collapse a group to hide its files."""
        if group_id in self._group_data:
            item_id = self._group_data[group_id]["item_id"]
            self._tree.item(item_id, open=False)
            self._group_data[group_id]["expanded"] = False

    def toggle_group(self, group_id: int) -> None:
        """Toggle a group's expanded state."""
        if group_id in self._group_data:
            if self._group_data[group_id]["expanded"]:
                self.collapse_group(group_id)
            else:
                self.expand_group(group_id)

    # -------------------------------------------------------------------------
    # File Management
    # -------------------------------------------------------------------------

    def add_file(
        self,
        group_id: int,
        file_id: str,
        name: str,
        size: str,
        modified: str,
        similarity: str,
        path: str,
        checked: bool = False,
    ) -> str:
        """
        Add a file to a group.

        Args:
            group_id: ID of the parent group
            file_id: Unique identifier for the file
            name: File name
            size: File size as string (e.g., "2.5 MB")
            modified: Modification date as string
            similarity: Similarity percentage as string
            path: Full file path
            checked: Initial checkbox state

        Returns:
            The treeview item ID for the file
        """
        if group_id not in self._group_data:
            raise ValueError(f"Group {group_id} does not exist")

        group_item_id = self._group_data[group_id]["item_id"]
        item_id = f"file_{file_id}"

        # Checkbox symbol
        checkbox = "[X]" if checked else "[ ]"

        # Insert the file
        self._tree.insert(
            group_item_id,
            tk.END,
            iid=item_id,
            text=checkbox,
            values=(
                name,
                size,
                modified,
                similarity,
                path,
            ),
            tags=("file", "even" if self._is_even_row(group_id, file_id) else "odd"),
        )

        # Store file data
        self._file_data[file_id] = {
            "group_id": group_id,
            "name": name,
            "size": size,
            "modified": modified,
            "similarity": similarity,
            "path": path,
            "checked": checked,
            "item_id": item_id,
        }

        self._file_to_group[file_id] = group_id

        return item_id

    def _is_even_row(self, group_id: int, file_id: str) -> bool:
        """Determine if a file row should have even coloring."""
        # Count files in this group that were added before this one
        count = 0
        group_item_id = self._group_data[group_id]["item_id"]
        for child_id in self._tree.get_children(group_item_id):
            if child_id == f"file_{file_id}":
                break
            count += 1
        return count % 2 == 0

    def set_file_checked(self, file_id: str, checked: bool) -> None:
        """
        Set the checked state of a file.

        Args:
            file_id: Unique identifier for the file
            checked: New checkbox state
        """
        if file_id not in self._file_data:
            return

        self._file_data[file_id]["checked"] = checked
        item_id = self._file_data[file_id]["item_id"]

        # Update checkbox display
        checkbox = "[X]" if checked else "[ ]"
        self._tree.item(item_id, text=checkbox)

        # Call callback
        if self._on_file_checked:
            group_id = self._file_data[file_id]["group_id"]
            self._on_file_checked(group_id, file_id, checked)

    def toggle_file_checked(self, file_id: str) -> None:
        """Toggle a file's checked state."""
        if file_id in self._file_data:
            checked = not self._file_data[file_id]["checked"]
            self.set_file_checked(file_id, checked)

    def select_group_files(self, group_id: int, checked: bool = True) -> None:
        """
        Select/deselect all files in a group.

        Args:
            group_id: ID of the group
            checked: True to select all, False to deselect all
        """
        if group_id not in self._group_data:
            return

        group_item_id = self._group_data[group_id]["item_id"]
        for child_id in self._tree.get_children(group_item_id):
            # Extract file_id from item_id
            if child_id.startswith("file_"):
                file_id = child_id[5:]  # Remove "file_" prefix
                self.set_file_checked(file_id, checked)

    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------

    def _on_tree_click(self, event: tk.Event) -> None:
        """Handle click events on the treeview."""
        region = self._tree.identify("region", event.x, event.y)

        if region == "tree":
            # Click on the tree column (checkbox area or expand/collapse)
            item_id = self._tree.identify_row(event.y)

            if item_id:
                if item_id.startswith("group_"):
                    # Click on group header - toggle expansion
                    group_id = int(item_id[6:])  # Remove "group_" prefix
                    self.toggle_group(group_id)
                elif item_id.startswith("file_"):
                    # Click on file - toggle checkbox
                    file_id = item_id[5:]  # Remove "file_" prefix
                    self.toggle_file_checked(file_id)

    def _on_tree_double_click(self, event: tk.Event) -> None:
        """Handle double-click events on the treeview."""
        item_id = self._tree.identify_row(event.y)

        if item_id and item_id.startswith("file_"):
            file_id = item_id[5:]  # Remove "file_" prefix
            if self._on_file_double_click:
                group_id = self._file_to_group.get(file_id, 0)
                self._on_file_double_click(group_id, file_id)

    def _on_column_click(self, column: str) -> None:
        """Handle column header clicks for sorting."""
        if column == self.COL_CHECKBOX:
            # Don't sort by checkbox column
            return

        # Toggle sort direction if clicking same column
        if self._sort_column == column:
            self._sort_ascending = not self._sort_ascending
        else:
            self._sort_column = column
            self._sort_ascending = True

        # Perform sort
        self._sort_treeview(column, self._sort_ascending)

    def _sort_treeview(self, column: str, ascending: bool) -> None:
        """Sort the treeview by the specified column."""
        # Sort groups
        group_ids = list(self._group_data.keys())

        if column == self.COL_NAME:
            group_ids.sort(
                key=lambda gid: self._group_data[gid]["name"],
                reverse=not ascending,
            )
        elif column == self.COL_SIZE:
            group_ids.sort(
                key=lambda gid: self._group_data[gid]["reclaimable_mb"],
                reverse=not ascending,
            )
        elif column == self.COL_SIMILARITY:
            # Sort by file count as proxy for similarity
            group_ids.sort(
                key=lambda gid: self._group_data[gid]["file_count"],
                reverse=not ascending,
            )
        else:
            # Default: sort by group ID
            group_ids.sort(reverse=not ascending)

        # Reorder groups in treeview
        for group_id in group_ids:
            group_item_id = self._group_data[group_id]["item_id"]
            self._tree.move(group_item_id, "", tk.END)

        # Sort files within each group
        for group_id in group_ids:
            group_item_id = self._group_data[group_id]["item_id"]
            file_items = list(self._tree.get_children(group_item_id))

            if column == self.COL_NAME:
                file_items.sort(
                    key=lambda iid: self._tree.item(iid)["values"][0],  # Name column
                    reverse=not ascending,
                )
            elif column == self.COL_SIZE:
                file_items.sort(
                    key=lambda iid: self._tree.item(iid)["values"][1],  # Size column
                    reverse=not ascending,
                )
            elif column == self.COL_MODIFIED:
                file_items.sort(
                    key=lambda iid: self._tree.item(iid)["values"][2],  # Modified column
                    reverse=not ascending,
                )
            elif column == self.COL_SIMILARITY:
                file_items.sort(
                    key=lambda iid: self._tree.item(iid)["values"][3],  # Similarity column
                    reverse=not ascending,
                )
            elif column == self.COL_PATH:
                file_items.sort(
                    key=lambda iid: self._tree.item(iid)["values"][4],  # Path column
                    reverse=not ascending,
                )

            # Reorder files in group
            for file_item_id in file_items:
                self._tree.move(file_item_id, group_item_id, tk.END)

    # -------------------------------------------------------------------------
    # Context Menu
    # -------------------------------------------------------------------------

    def _on_context_menu(self, event: tk.Event) -> None:
        """Show context menu on right-click."""
        item_id = self._tree.identify_row(event.y)

        if not item_id:
            return

        # Create context menu
        context_menu = tk.Menu(self._tree, tearoff=tk.FALSE)

        if item_id.startswith("file_"):
            file_id = item_id[5:]
            if file_id in self._file_data:
                file_data = self._file_data[file_id]
                path = file_data["path"]

                # Add file-specific options
                context_menu.add_command(
                    label="Open File",
                    command=lambda: self._open_file(path),
                )
                context_menu.add_command(
                    label="Open Folder",
                    command=lambda: self._open_folder(path),
                )
                context_menu.add_separator()
                context_menu.add_command(
                    label="Copy Path",
                    command=lambda: self._copy_path(path),
                )

        elif item_id.startswith("group_"):
            group_id = int(item_id[6:])

            # Add group-specific options
            context_menu.add_command(
                label="Select All in Group",
                command=lambda: self.select_group_files(group_id, True),
            )
            context_menu.add_command(
                label="Deselect All in Group",
                command=lambda: self.select_group_files(group_id, False),
            )

        # Show menu
        context_menu.post(event.x_root, event.y_root)

    def _open_file(self, path: str) -> None:
        """Open a file with the system's default application."""
        try:
            if platform.system() == "Windows":
                subprocess.run(["start", "", path], shell=True, check=True)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", path], check=True)
            else:  # Linux
                subprocess.run(["xdg-open", path], check=True)
        except (subprocess.SubprocessError, OSError) as e:
            print(f"Failed to open file {path}: {e}")

    def _open_folder(self, path: str) -> None:
        """Open the folder containing a file."""
        try:
            folder_path = str(Path(path).parent)

            if platform.system() == "Windows":
                subprocess.run(["explorer", folder_path], shell=True, check=True)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", folder_path], check=True)
            else:  # Linux
                subprocess.run(["xdg-open", folder_path], check=True)
        except (subprocess.SubprocessError, OSError) as e:
            print(f"Failed to open folder {path}: {e}")

    def _copy_path(self, path: str) -> None:
        """Copy a file path to the clipboard."""
        self.clipboard_clear()
        self.clipboard_append(path)
        self.update()

    # -------------------------------------------------------------------------
    # Data Access
    # -------------------------------------------------------------------------

    def get_file_data(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get data for a specific file.

        Args:
            file_id: Unique identifier for the file

        Returns:
            Dictionary containing file data, or None if not found
        """
        return self._file_data.get(file_id)

    def get_group_data(self, group_id: int) -> Optional[Dict[str, Any]]:
        """
        Get data for a specific group.

        Args:
            group_id: Unique identifier for the group

        Returns:
            Dictionary containing group data, or None if not found
        """
        return self._group_data.get(group_id)

    def get_checked_files(self) -> List[Dict[str, Any]]:
        """
        Get all files that are checked.

        Returns:
            List of file data dictionaries for checked files
        """
        return [
            file_data
            for file_data in self._file_data.values()
            if file_data["checked"]
        ]

    def get_all_files(self) -> List[Dict[str, Any]]:
        """
        Get all files in the treeview.

        Returns:
            List of all file data dictionaries
        """
        return list(self._file_data.values())

    def clear(self) -> None:
        """Clear all data from the treeview."""
        self._tree.delete(*self._tree.get_children())
        self._group_data.clear()
        self._file_data.clear()
        self._file_to_group.clear()
        self._group_counter = 0


__all__ = ["CheckTreeview"]
