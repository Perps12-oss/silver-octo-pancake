# Phase 2 Integration Strategy

## Overview

This document maps the integration points between the ScanOrchestrator engine and the UI components for wiring the full scan-to-delete workflow.

---

## 1. Orchestrator API Analysis

**File:** `cerebro/engines/orchestrator.py`

### Key Methods
- `set_mode(mode: str) -> List[EngineOption]`: Switch to scan mode, return options
- `start_scan(folders, protected, options, progress_callback)`: Start scan in background
- `pause()`, `resume()`, `cancel()`: Control active scan
- `get_results() -> List[DuplicateGroup]`: Get scan results
- `get_progress() -> ScanProgress`: Get current progress snapshot
- `is_scanning()`, `is_paused()`, `is_completed()`: Query scan state

### Data Types
- **ScanProgress** (from `base_engine`/`models.py`): phase, message, percent, scanned_files, scanned_bytes, elapsed_seconds, estimated_totals, speed, throughput, eta, warnings, groups_found, current_path
- **DuplicateGroup** (from `models.py`): group_id, files (List[FileMetadata]), group_hash, visual_score, cluster_distance, tags, metadata
- **FileMetadata**: path, size, mtime, is_symlink, is_hidden, extension, hash_partial, hash_full, tags, metadata

---

## 2. Engine API Analysis

**File:** `cerebro/engines/file_dedup_engine.py`

### Key Methods
- `configure(folders, protected, options)`: Set scan parameters
- `start(progress_callback)`: Start scan (threaded)
- `pause()`, `resume()`, `cancel()`: Control scan
- `get_results() -> List[DuplicateGroup]`: Return results
- `get_progress() -> ScanProgress`: Return progress

### Progress Callback Signature
```python
def progress_callback(progress: ScanProgress) -> None:
    # Called periodically during scan
    # Should update status_bar widgets
```

---

## 3. UI Component Analysis

### FolderPanel
**File:** `cerebro/v2/ui/folder_panel.py`

**Methods:**
- `get_scan_folders() -> List[Path]`: Get folders to scan
- `get_protected_folders() -> List[Path]`: Get protected folders
- `get_options() -> Dict`: Get scan options (mode-specific)
- `set_scan_mode(mode: str)`: Update options for new mode
- `on_folders_changed(callback)`, `on_protected_changed(callback)`: Set callbacks

### StatusBar
**File:** `cerebro/v2/ui/status_bar.py`

**Methods:**
- `update_metrics(StatusBarMetrics)`: Update all displayed metrics
- `update_scanned(count)`, `update_duplicates(count)`, `update_groups(count)`
- `update_reclaimable(bytes)`, `update_elapsed(seconds)`
- `update_progress(percent)`: Update progress bar
- `set_scanning(bool)`: Show/hide progress bar
- `start_polling(callback, interval)`, `stop_polling()`

**StatusBarMetrics:** files_scanned, duplicates_found, groups_found, bytes_reclaimable, elapsed_seconds, is_scanning, progress_percent

### ResultsPanel
**File:** `cerebro/v2/ui/results_panel.py`

**Methods:**
- `load_results(groups: List[DuplicateGroup])`: Display duplicate groups
- `get_selected_files() -> List[Dict]`: Get checked files for deletion
- `get_reclaimable_space() -> int`: Calculate reclaimable bytes
- `get_selected_count() -> int`, `get_total_count() -> int`
- `apply_selection_rule(rule: str)`: "select_all", "select_except_largest", etc.
- `on_selection_changed(callback)`, `on_file_selected(callback)`
- `set_mode(mode: str)`: Update columns for scan mode
- `clear()`: Clear all results

**Local DuplicateGroup class** (different from core.models):
- group_id: int
- files: List[Dict[str, Any]] (with path, size, modified, similarity, checked)
- total_size: int
- reclaimable: int

### PreviewPanel
**File:** `cerebro/v2/ui/preview_panel.py`

**Methods:**
- `load_single(file_data: Dict)`: Load one file
- `load_comparison(file_a: Dict, file_b: Dict)`: Load two files for comparison
- `load_file_a(file_data)`, `load_file_b(file_data)`
- `clear()`: Clear previews
- `on_keep_a(callback)`, `on_keep_b(callback)`: Set callbacks for keep buttons

**File data dict format:** path, size, modified, width, height, similarity

### TrashManager
**File:** `cerebro/core/safety/trash_manager.py`

**Methods:**
- `move_duplicates(groups: List[DuplicateGroup], scan_root: Path) -> TrashAction`: Move selected files to trash
- `undo(action: TrashAction) -> bool`: Restore moved files

---

## 4. Integration Mapping

### 4.1 Folders -> Orchestrator (Start Scan)

```
MainWindow._on_start_search()
  |
  +-- folder_panel.get_scan_folders() -> List[Path]
  |       |
  |       v
  +-- folder_panel.get_protected_folders() -> List[Path]
  |       |
  |       v
  +-- folder_panel.get_options() -> Dict
  |       |
  |       v
  +-- orchestrator.set_mode(current_mode) -> get EngineOption list
  |       |
  |       v
  +-- orchestrator.start_scan(folders, protected, options, progress_callback)
```

### 4.2 Progress Callback -> Status Bar

```
progress_callback(progress: ScanProgress)
  |
  +-- status_bar.update_metrics(StatusBarMetrics(
  |       files_scanned=progress.scanned_files,
  |       duplicates_found=progress.scanned_files - len(unique),  // calc from engine
  |       groups_found=progress.groups_found,
  |       bytes_reclaimable=calc_from_results(),
  |       elapsed_seconds=progress.elapsed_seconds,
  |       is_scanning=True,
  |       progress_percent=progress.percent
  |   ))
```

**Note:** Need to map ScanProgress fields to StatusBarMetrics. Some fields like `duplicates_found` and `bytes_reclaimable` may need to be derived from results when scan completes.

### 4.3 DuplicateGroup -> ResultsPanel (Display Results)

```
orchestrator.get_results() -> List[DuplicateGroup] (core.models)
  |
  v
Transform to ResultsPanel.DuplicateGroup format:
  For each core.DuplicateGroup:
    - group_id: int
    - total_size: sum(f.size for f in files)
    - reclaimable: sum(f.size for f in files[1:])  // exclude keeper
    - files: List[Dict]:
        {
            "path": str(file.path),
            "size": file.size,
            "modified": file.mtime,
            "similarity": 1.0 (for exact) or visual_score,
            "checked": False,
            "extension": file.extension
        }
  |
  v
results_panel.load_results(transformed_groups)
```

### 4.4 File Selection -> PreviewPanel

```
results_panel._on_selection_changed(item_id)
  |
  +-- Parse item_id (format: "group_index_file_index")
  |
  +-- Get file data from group
  |
  v
preview_panel.load_single(file_data)
  OR
preview_panel.load_comparison(file_a, file_b)  // for two selected files
```

### 4.5 Delete -> send2trash via TrashManager

```
MainWindow._on_delete_selected()
  |
  +-- results_panel.get_selected_files() -> List[Dict]
  |
  +-- Build DeletionRequest or prepare DuplicateGroup list
  |
  v
trash_manager.move_duplicates(prepared_groups, scan_root)
  |
  +-- Move files to .cerebro_trash (in scan root)
  |
  v
Update UI:
  - Remove deleted files from results_panel
  - Update status_bar reclaimable
  - Show confirmation message
```

---

## 5. Data Transformation Requirements

### ScanProgress -> StatusBarMetrics

| ScanProgress Field | StatusBarMetrics Field | Notes |
|-------------------|----------------------|-------|
| scanned_files | files_scanned | Direct mapping |
| percent | progress_percent | Direct mapping (0-100) |
| elapsed_seconds | elapsed_seconds | Direct mapping |
| groups_found | groups_found | Direct mapping |
| - | duplicates_found | Calc: total_scanned - unique_files |
| - | bytes_reclaimable | Calc from results after scan |
| state == SCANNING | is_scanning | Boolean conversion |

### core.DuplicateGroup -> results.DuplicateGroup

```python
def transform_group(core_group: core.DuplicateGroup) -> results.DuplicateGroup:
    files_dict = [
        {
            "path": str(f.path),
            "size": f.size,
            "modified": f.mtime,
            "similarity": 1.0,  # or core_group.visual_score / 100
            "checked": False,
            "extension": f.extension or Path(f.path).suffix.lower()
        }
        for f in core_group.files
    ]

    total_size = sum(f.size for f in core_group.files)
    # Reclaimable = sum of all except keeper (largest file)
    if core_group.files:
        max_size = max(f.size for f in core_group.files)
        reclaimable = sum(f.size for f in core_group.files if f.size != max_size)
    else:
        reclaimable = 0

    return results.DuplicateGroup(
        group_id=core_group.group_id,
        files=files_dict,
        total_size=total_size,
        reclaimable=reclaimable
    )
```

---

## 6. Implementation Order

1. **Phase 2a: Wire Start/Stop**
   - Create ScanOrchestrator instance in MainWindow
   - Wire Toolbar start/stop buttons to orchestrator methods
   - Wire folder_panel callbacks to update internal state

2. **Phase 2b: Wire Progress**
   - Implement progress_callback in MainWindow
   - Map ScanProgress to StatusBarMetrics
   - Update status_bar on progress updates

3. **Phase 2c: Wire Results Display**
   - Implement results transformation (core -> results panel format)
   - Call results_panel.load_results() after scan completes
   - Update status_bar with final metrics

4. **Phase 2d: Wire Preview**
   - Wire results panel file selection to preview panel
   - Implement file data dict preparation for preview
   - Handle single and comparison preview modes

5. **Phase 2e: Wire Delete**
   - Integrate TrashManager
   - Wire delete button to trash_manager.move_duplicates()
   - Update UI after deletion
   - Implement undo (optional)

---

## 7. Open Questions

1. **Progress mapping:** ScanProgress doesn't provide `duplicates_found` during scan. Should this be 0 until scan completes, or should we maintain a running count in MainWindow?

2. **Result transformation:** Should transformation happen in MainWindow or in a helper module?

3. **Trash location:** Should TrashManager use a configurable trash directory, or always use `.cerebro_trash` in scan root?

4. **Undo implementation:** Should we implement full undo with TrashManager.undo(), or keep it simple for now?

5. **Error handling:** How should engine errors be displayed to the user? Status bar message, dialog, or both?
