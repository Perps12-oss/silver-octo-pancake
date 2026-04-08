# Cerebro v2 — UI Overhaul & Full Migration Plan

> **Purpose:** Fix all UI discrepancies vs Ashisoft + complete remaining Phases 4-6
> **Priority:** CRITICAL — app is non-functional without delete wiring
> **Based on:** Screenshot audit of current Cerebro vs Ashisoft Duplicate File Finder Pro 8.2
> **Last updated:** April 2026

---

## Table of Contents

1. [Screenshot Audit — Every Problem Identified](#1-screenshot-audit)
2. [Ashisoft UI Reference — What It Actually Looks Like](#2-ashisoft-reference)
3. [Corrective Phase A — Critical Bugs & Missing Wiring](#3-phase-a)
4. [Corrective Phase B — Navigation Bar Overhaul](#4-phase-b)
5. [Corrective Phase C — Left Panel Restructure](#5-phase-c)
6. [Corrective Phase D — Results Panel & Actions](#6-phase-d)
7. [Corrective Phase E — Preview Panel Polish](#7-phase-e)
8. [Phase 4 — Video & Music Engines](#8-phase-4)
9. [Phase 5 — Utility Tools (Empty Folders + Large Files)](#9-phase-5)
10. [Phase 6 — Selection Assistant & Premium Polish](#10-phase-6)
11. [Phase 7 — VS Code Theme System Integration](#11-phase-7)
12. [Complete Task Checklist](#12-checklist)

---

## 1. Screenshot Audit — Every Problem Identified

### Current state from screenshot

```
┌─ Cerebro v2 ────────────────────────────────────────── [─][□][×] ─┐
│ [?]                                        (huge empty gap)        │
│                                                                    │
│ [Files] [Photos] [Videos] [Music] [Empty Folders] [Large Files]    │  ← MODE TABS (flat, no icons, no visual weight)
│                                                                    │
│ ┌─Scan Folders──┐ [All][Images][Videos][Documents][Audio][Other]    │  ← SUB-FILTER TABS (misplaced — should be inside results)
│ │ [+ Add Path]  │                                                  │
│ ├─Protect Fldrs─┤  "CheckTreeview widget will be implemented       │  ← PLACEHOLDER TEXT (results area not built)
│ │ [+ Protect]   │   in ui/widgets/"                                │
│ ├─Scan Options──┤                                                  │
│ │ (cut off text)│                                                  │
│ └───────────────┘                                                  │
│                                                                    │
│ [Select all except largest ▼] [Apply] 0 of 0 [SelectAll][Desel][Invert] [Delete Selected] │  ← SELECTION BAR (correct concept, wrong placement)
│                                                                    │
│ Preview                                                   [▼][Diff]│
│ ┌──────────────────────┐  ┌──────────────────────┐                 │
│ │                      │  │                      │                 │  ← PREVIEW (takes 50% of screen — way too much)
│ │                      │  │                      │                 │
│ │                      │  │                      │                 │
│ └──────────────────────┘  └──────────────────────┘                 │
│ [─] A Resolution: —       [─] B Resolution: —                      │
│     A Size: —                  B Size: —                           │
│     A Modified: —              B Modified: —                       │
│     EXIF: —                    EXIF: —                             │
│         [Keep A]                   [Keep B]                        │
│                                                                    │
│ Scanned: 0 | Dupes: 0 | Groups: 0 | Reclaimable: 0 B  [●━━] Ready│
│ Elapsed: 0:00                                                      │
└────────────────────────────────────────────────────────────────────┘
```

### Problems identified (18 total)

#### CRITICAL (blocks basic functionality)

| # | Problem | Severity | Detail |
|---|---------|----------|--------|
| C1 | **No Start Search button** | CRITICAL | There is no way to initiate a scan. Ashisoft has a prominent "Start Search" button in the toolbar. We have nothing. |
| C2 | **No Delete button wired** | CRITICAL | "Delete Selected" button exists visually but is not wired to `send2trash` or any deletion logic. The app cannot delete files. |
| C3 | **Results area is a placeholder** | CRITICAL | Center panel shows "CheckTreeview widget will be implemented in ui/widgets/" — the actual results treeview with grouped duplicates does not exist yet. |
| C4 | **No Add Path / Start Search toolbar** | CRITICAL | Ashisoft has a top toolbar with "Add Folders", "Start Search", "Auto Mark", "Delete", "Settings" as prominent buttons. We have none of these — only a tiny "?" button in the corner. |

#### HIGH (fundamentally wrong layout)

| # | Problem | Severity | Detail |
|---|---------|----------|--------|
| H1 | **Mode tabs are flat text, not navigational** | HIGH | Ashisoft's mode tabs are large, icon-bearing tabs that switch the ENTIRE page layout. Ours are flat `CTkSegmentedButton` text labels that look like filters, not navigation. |
| H2 | **Left panel is crammed** | HIGH | Three collapsible sections (Scan Folders, Protect Folders, Scan Options) fight for ~200px of vertical space. "Scan Options" text is cut off. In Ashisoft, the left panel ONLY shows the folder list — options and protect are in separate tabs/dialogs. |
| H3 | **Sub-filter tabs (All/Images/Videos/etc.) are at the wrong level** | HIGH | These sit at the same level as the left panel header, spanning both panels. In Ashisoft, these sub-tabs are INSIDE the results area, below the toolbar, above the results list. |
| H4 | **No toolbar at all** | HIGH | Ashisoft has a full toolbar row with: Add Folders, Remove, Search Now, Auto Mark dropdown, Delete, Move To, Settings, Help. We have nothing between the title bar and the mode tabs — just a lonely "?" button. |
| H5 | **Preview panel dominates the screen** | HIGH | The preview+metadata+Keep buttons take ~50% of the visible window. In Ashisoft, the preview is a compact panel that only shows when you select files, and takes ~25% max. |
| H6 | **Selection bar is a separate floating strip** | HIGH | In Ashisoft, the selection assistant ("Auto Mark") is a DROPDOWN in the toolbar, not a separate bar. Our implementation adds a dedicated bar that eats vertical space. |

#### MEDIUM (visual/UX issues)

| # | Problem | Severity | Detail |
|---|---------|----------|--------|
| M1 | **Huge empty gap between title bar and mode tabs** | MEDIUM | ~40px of dead space between the window title and the first content row. |
| M2 | **Mode tabs stretch full width** | MEDIUM | Each tab is ~1/6 of the window width. Ashisoft's tabs are compact, left-aligned, and only as wide as needed. |
| M3 | **No visual hierarchy** | MEDIUM | Everything is the same dark color. No distinction between toolbar, navigation, content area, and status. Ashisoft uses subtle background shading to separate zones. |
| M4 | **"Keep A" / "Keep B" buttons in preview** | MEDIUM | Not an Ashisoft feature. Ashisoft uses checkboxes in the results list, not keep buttons in the preview. |
| M5 | **Two status bar rows** | MEDIUM | "Scanned: 0 | Dupes: 0..." on one line, "Elapsed: 0:00" on another. Ashisoft has a single status bar line. |
| M6 | **No drag-and-drop visual cue** | MEDIUM | Ashisoft shows a prominent drop zone for folders. We don't. |
| M7 | **Scrollbar artifacts** | MEDIUM | Small scrollbar handles visible on the left panel sections even when empty. |
| M8 | **No settings/gear button** | MEDIUM | No way to access settings from the main window. |

---

## 2. Ashisoft UI Reference — What It Actually Looks Like

Based on every screenshot I've analyzed from Ashisoft's website, help pages, and third-party reviews, here's the actual Ashisoft layout:

### Pre-scan state (what you see when you open the app)

```
┌─ Ashisoft Duplicate File Finder Pro ─────────────────────────────────┐
│ ┌─────────────────────── TOOLBAR ──────────────────────────────────┐ │
│ │ [📁 Add Folders] [✕ Remove] [🔍 Search Now] [📋 Auto Mark ▼]   │ │
│ │ [🗑 Delete] [📦 Move To] [⚙ Settings] [❓ Help]                │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│ ┌── MODE TABS (icon + text, compact) ─────────────────────────────┐ │
│ │ [📄Files] [☁Cloud] [🎵Music] [⚡Compare] [📁Folders] [🔷Unique]│ │
│ └──────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│ ┌─ LEFT: Folder List ──┐ ┌─ RIGHT: Main Content Area ────────────┐ │
│ │                       │ │                                       │ │
│ │  📁 C:\Users\Photos   │ │  "Add folders and click Search Now    │ │
│ │  📁 D:\Backup         │ │   to find duplicate files"            │ │
│ │  📁 E:\Downloads      │ │                                       │ │
│ │                       │ │  [📁 Add Folders]  [🔍 Search Now]    │ │
│ │                       │ │                                       │ │
│ │  ─────────────────    │ │  (helpful getting-started text with   │ │
│ │  Scan Settings:       │ │   numbered steps and illustrations)   │ │
│ │  ○ By Content (SHA)   │ │                                       │ │
│ │  ○ By Name + Size     │ │                                       │ │
│ │  Min size: [0 KB]     │ │                                       │ │
│ │                       │ │                                       │ │
│ └───────────────────────┘ └───────────────────────────────────────┘ │
│                                                                      │
│ ┌─ STATUS BAR ────────────────────────────────────────────────────┐ │
│ │ Ready                                                           │ │
│ └──────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### Post-scan state (after clicking Search Now)

```
┌─ Ashisoft Duplicate File Finder Pro ─────────────────────────────────┐
│ ┌─────────────────────── TOOLBAR ──────────────────────────────────┐ │
│ │ [📁 Add Folders] [✕ Remove] [🔍 Search Now] [📋 Auto Mark ▼]   │ │
│ │ [🗑 Delete] [📦 Move To] [⚙ Settings] [❓ Help]                │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│ ┌── MODE TABS ────────────────────────────────────────────────────┐ │
│ │ [📄Files] [☁Cloud] [🎵Music] [⚡Compare] [📁Folders] [🔷Unique]│ │
│ └──────────────────────────────────────────────────────────────────┘ │
│ ┌── RESULT TYPE FILTER TABS ─────────────────────────────────────┐  │
│ │ [All (347)] [Audio (89)] [Video (45)] [Images (120)] [Docs (93)]│  │
│ └──────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│ ┌─ RESULTS LIST (full width, no left panel during results) ──────┐ │
│ │ ☐ Name              │ Size    │ Modified    │ Similarity │ Path │ │
│ │ ═══ Group 1 (3 files, 12.4 MB reclaimable) ═══════════════════ │ │
│ │ ☐ photo_001.jpg      4.2 MB   2024-03-15    100%    C:\Photos  │ │
│ │ ☑ photo_001(1).jpg   4.2 MB   2024-01-02    100%    D:\Backup  │ │
│ │ ☑ copy_photo.jpg     4.1 MB   2023-12-20    100%    E:\Down... │ │
│ │ ═══ Group 2 (2 files, 8.1 MB reclaimable) ═══════════════════  │ │
│ │ ☐ report.docx        4.1 MB   2025-01-10    100%    C:\Docs    │ │
│ │ ☑ report_copy.docx   4.0 MB   2024-11-05    100%    D:\Backup  │ │
│ │ ...                                                             │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│ ┌─ PREVIEW (compact, only visible when image/video selected) ────┐ │
│ │ [Image A]                        [Image B]                      │ │
│ │ 4032×3024 | 4.2MB | JPG          4032×3024 | 4.1MB | JPG       │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│ ┌─ STATUS BAR ────────────────────────────────────────────────────┐ │
│ │ Scanned: 12,847 | Duplicates: 347 | Groups: 89 | Reclaimable: 2.4 GB | 00:01:23 │
│ └──────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### Key observations from Ashisoft

1. **The toolbar IS the action center.** Add, Remove, Search, Auto Mark, Delete, Move, Settings — all in one row. Not scattered across panels.
2. **Mode tabs switch the ENTIRE content area.** "Files" mode shows file-specific options. "Music" mode shows tag-matching options. "Compare" mode shows master/target folder layout. Each tab is a different page.
3. **Left panel disappears after scan.** Pre-scan: left panel shows folder list + scan settings. Post-scan: left panel is gone, results take full width.
4. **Result type filter tabs appear ONLY after scan.** They sit above the results list, not above the content area.
5. **Preview is compact and context-sensitive.** Only shows for images/videos. Takes minimal space.
6. **Auto Mark is a dropdown menu in the toolbar**, not a separate bar.

---

## 3. Corrective Phase A — Critical Bugs & Missing Wiring

> **Priority:** DO THIS FIRST — the app is non-functional without these
> **Estimated effort:** 1 session

### A1. Wire "Delete Selected" to send2trash

```python
# In selection_bar.py or results_panel.py:
def _on_delete_selected(self):
    checked = self.results_treeview.get_checked_items()
    if not checked:
        return

    total_size = sum(item.size for item in checked)
    count = len(checked)

    # Confirmation dialog
    if not messagebox.askyesno(
        "Delete Duplicates",
        f"Send {count} files to Recycle Bin?\n"
        f"This will free {fmt_bytes(total_size)}.\n\n"
        f"Files can be restored from the Recycle Bin.",
        icon="warning"
    ):
        return

    errors = []
    for item in checked:
        try:
            send2trash.send2trash(str(item.path))
        except Exception as e:
            errors.append((item.path, str(e)))

    # Remove deleted items from treeview
    self.results_treeview.remove_checked()
    self._update_counters()

    if errors:
        messagebox.showwarning(
            "Some files could not be deleted",
            f"{len(errors)} files failed:\n" +
            "\n".join(f"  {p}: {e}" for p, e in errors[:5])
        )
```

### A2. Build the actual CheckTreeview widget

The results panel currently shows placeholder text. We need the real `ttk.Treeview` with checkbox support, grouped rows, and sortable columns. This was specified in Phase 1 but not implemented.

### A3. Add Start Search button to toolbar

This is the most visible missing element. Must be prominent, accent-colored, and wired to the orchestrator.

### A4. Wire folder panel → orchestrator → results

The data flow: folders from left panel → orchestrator.start_scan() → progress updates to status bar → results to treeview.

### Deliverables

| File | Action | Description |
|------|--------|-------------|
| `ui/toolbar.py` | REWRITE | Add all Ashisoft toolbar buttons |
| `ui/widgets/check_treeview.py` | CREATE | Actual ttk.Treeview with checkboxes |
| `ui/results_panel.py` | REWRITE | Wire CheckTreeview, populate from engine results |
| `ui/selection_bar.py` | MODIFY | Wire delete button to send2trash |
| `ui/main_window.py` | MODIFY | Wire toolbar → orchestrator → results data flow |

---

## 4. Corrective Phase B — Navigation Bar Overhaul

> **Priority:** HIGH — the current nav looks nothing like Ashisoft
> **Estimated effort:** 1-2 sessions

### What's wrong now

The top of the window is:
1. Title bar with tiny "?" button (40px of wasted space)
2. Mode tabs as flat `CTkSegmentedButton` stretching full width
3. Result filter tabs (All/Images/Videos/etc.) misplaced at content level

### What Ashisoft has

1. **Toolbar row** — full-width bar with icon buttons: Add Folders, Remove, Search Now, Auto Mark dropdown, Delete, Move To, Settings, Help
2. **Mode tabs row** — compact tabs with icons, left-aligned, each switching the entire content page
3. Result filter tabs appear ONLY inside the results area after a scan

### The fix

#### New toolbar (replaces the empty gap + "?" button)

```
┌──────────────────────────────────────────────────────────────────┐
│ [📁 Add Path] [✕ Remove] │ [▶ Search Now] [⏹ Stop] │          │
│ [📋 Auto Mark ▼] [🗑 Delete] [📦 Move To] │ [⚙] [❓]         │
└──────────────────────────────────────────────────────────────────┘
```

- Buttons grouped with visual separators (| dividers)
- "Search Now" is accent-colored (cyan) and larger
- "Stop" is hidden until a scan is running
- "Delete" is danger-colored (red)
- Settings and Help are icon-only buttons on the right

#### New mode tabs (replaces the flat segmented button)

```
┌─────────────────────────────────────────────────────┐
│ [📄 Files] [🖼 Photos] [🎬 Videos] [🎵 Music]     │
│ [📁 Empty Folders] [📊 Large Files]                 │
└─────────────────────────────────────────────────────┘
```

- Each tab has an icon + text label
- Tabs are left-aligned, compact width (not stretched)
- Active tab has accent bottom border + slightly elevated background
- Clicking a tab switches the ENTIRE content area below (like browser tabs)
- Each tab has its own page layout (different left panel, different results columns)

#### Result filter tabs (moved inside results area)

```
[All (347)] [Images (120)] [Videos (45)] [Audio (89)] [Docs (93)]
```

- Only visible after a scan completes
- Sits immediately above the results treeview
- Filters the visible results without re-scanning
- Shows count per type in parentheses

### Deliverables

| File | Action | Description |
|------|--------|-------------|
| `ui/toolbar.py` | REWRITE | Full Ashisoft-style toolbar with all buttons |
| `ui/mode_tabs.py` | REWRITE | Icon tabs, compact, left-aligned, page-switching |
| `ui/results_panel.py` | MODIFY | Add result filter tabs inside results area |
| `ui/main_window.py` | MODIFY | Wire mode tab switching to page swap logic |

---

## 5. Corrective Phase C — Left Panel Restructure

> **Priority:** HIGH — left panel is cramped and fights for space
> **Estimated effort:** 1 session

### What's wrong now

Three collapsible sections crammed into ~200px width:
- "Scan Folders" with "+ Add Path" button
- "Protect Folders" with "+ Protect" button
- "Scan Options" with text that gets cut off

This causes: text truncation, scrollbar artifacts, no room to actually see folder paths, options are invisible.

### What Ashisoft does

The left panel is **mode-dependent** and **state-dependent**:

**Pre-scan (Files mode):**
- Folder list (full height) showing added paths with remove buttons
- Below: minimal scan settings (comparison method dropdown, min size)
- "Protect folders" is a TAB within the left panel, not a squished section

**Pre-scan (Music mode):**
- Folder list
- Below: tag match options (checkboxes for Title, Artist, Album)

**Pre-scan (Compare mode):**
- Master folder selector
- Target folders list

**Post-scan (all modes):**
- Left panel either HIDES entirely (results go full width) OR shrinks to a narrow folder reference strip

### The fix

#### Tab-based left panel (not collapsible sections)

```
┌── LEFT PANEL ──────────────┐
│ [📁 Folders] [🛡 Protect]  │  ← TWO TABS (not three squished sections)
│                             │
│ Pre-scan (Folders tab):     │
│  C:\Users\Steve\Photos     ✕│
│  D:\Backup                 ✕│
│  E:\Downloads              ✕│
│                             │
│  [+ Add Folder]             │
│  [+ Add Drive]              │
│                             │
│  ─── Scan Settings ───      │
│  Method: [SHA256 ▼]         │
│  Min size: [0 KB    ]       │
│  Skip: [.sys, .dll  ]       │
│                             │
│  [▶ Search Now]             │  ← SECONDARY search button (duplicates toolbar for convenience)
└─────────────────────────────┘
```

#### State-dependent behavior

- **Pre-scan:** Left panel visible at ~250px, shows folders + settings
- **Scanning:** Left panel stays visible, shows progress indicator
- **Post-scan:** Left panel collapses to ~0px, results take full width. A small "Show Folders" toggle in the toolbar can re-expand it.

### Deliverables

| File | Action | Description |
|------|--------|-------------|
| `ui/folder_panel.py` | REWRITE | Tab-based (Folders/Protect), mode-dependent settings |
| `ui/main_window.py` | MODIFY | Left panel collapse on scan complete, expand on new scan |

---

## 6. Corrective Phase D — Results Panel & Actions

> **Priority:** HIGH — results area doesn't exist yet
> **Estimated effort:** 2 sessions

### What needs to happen

The current results area shows placeholder text. We need:

1. **CheckTreeview widget** — ttk.Treeview with:
   - Checkbox column (☐/☑) toggled by click
   - Grouped rows: parent = group header, children = files
   - Columns: Checkbox, Name, Size, Modified, Similarity %, Path
   - Sortable by clicking any column header
   - Alternating row colors within groups
   - Right-click context menu: Open File, Open Folder, Copy Path, Select Group, Properties
   - Virtual scrolling for 10K+ rows

2. **Group headers** — colored/bold rows showing: "Group N — X files, Y MB reclaimable"

3. **Result type filter tabs** — "All (347) | Images (120) | Videos (45) | Audio (89) | Docs (93) | Other (0)" — only visible post-scan

4. **Empty state** — pre-scan, show a getting-started view (like Ashisoft):
   - "Add folders and click Search Now to find duplicate files"
   - Large "Add Folders" and "Search Now" buttons
   - Brief numbered instructions

5. **Scanning state** — during scan, show:
   - Progress bar
   - "Scanning: C:\Users\Steve\Photos\vacation\photo_001.jpg"
   - Live counters: files scanned, duplicates found so far

### Deliverables

| File | Action | Description |
|------|--------|-------------|
| `ui/widgets/check_treeview.py` | CREATE | Full checkbox treeview implementation |
| `ui/results_panel.py` | REWRITE | Three states: empty/scanning/results |
| `ui/results_filter_bar.py` | CREATE | Post-scan type filter tabs with counts |
| `ui/empty_state.py` | CREATE | Getting-started view for pre-scan |

---

## 7. Corrective Phase E — Preview Panel Polish

> **Priority:** MEDIUM — functional but oversized
> **Estimated effort:** 1 session

### What's wrong now

- Preview takes ~50% of window height
- Shows even when empty (nothing selected)
- "Keep A" / "Keep B" buttons aren't in Ashisoft
- Metadata labels visible but empty (dashes everywhere)

### The fix

1. **Collapse by default** — preview is hidden until a file is selected in results
2. **Compact mode** — when visible, takes only ~150px height for images, ~80px for file info
3. **Remove "Keep A" / "Keep B"** — selection happens via checkboxes in results, not keep buttons
4. **Context-sensitive** — only shows image preview for image files, video thumbnail for videos, metadata-only for documents
5. **Resizable** — user can drag divider to make preview taller/shorter

### Deliverables

| File | Action | Description |
|------|--------|-------------|
| `ui/preview_panel.py` | REWRITE | Collapsed by default, compact, context-sensitive |
| `ui/main_window.py` | MODIFY | Preview toggle via toolbar button or double-click |

---

## 8. Phase 4 — Video & Music Engines

> **Priority:** Normal — engines only, UI already handled by mode tab system
> **Estimated effort:** 2 sessions

### Video engine (engines/video_dedup_engine.py)

- FFmpeg subprocess for frame extraction (3-5 keyframes per video)
- Duration/size pre-filtering
- dHash comparison on extracted frames
- Graceful disable when FFmpeg not installed (video tab grays out with install prompt)
- Cache frame hashes in SQLite

### Music engine (engines/music_dedup_engine.py)

- mutagen for ID3 tag extraction (title, artist, album, duration, bitrate)
- Fuzzy string matching via SequenceMatcher (artist + title normalized)
- Duration tolerance ±2 seconds
- Keeper selection: FLAC > WAV > OGG > M4A > MP3, highest bitrate within format

### Deliverables

| File | Action | Description |
|------|--------|-------------|
| `engines/video_dedup_engine.py` | CREATE | FFmpeg + pHash pipeline |
| `engines/music_dedup_engine.py` | CREATE | ID3 tag fuzzy matching |
| `engines/orchestrator.py` | MODIFY | Register video + music engines |
| `ui/folder_panel.py` | MODIFY | Video-specific and music-specific scan options |

---

## 9. Phase 5 — Utility Tools

> **Priority:** Normal — quick wins, stdlib only
> **Estimated effort:** 1 session

### Empty folders engine

- Recursive `os.walk(topdown=False)`
- Detect nested empty trees
- Results as flat list (no grouping)
- Delete action removes empty directories

### Large files engine

- Single-pass stat collection → sort by size → top N
- Group by file type in results
- Show percentage of total scanned space
- No delete by default (informational) — optional "Move To" action

### Deliverables

| File | Action | Description |
|------|--------|-------------|
| `engines/empty_folder_engine.py` | CREATE | ~100 lines, stdlib only |
| `engines/large_file_engine.py` | CREATE | ~120 lines, stdlib only |
| `engines/orchestrator.py` | MODIFY | Register both engines |

---

## 10. Phase 6 — Selection Assistant & Premium Polish

> **Priority:** Normal — enhances usability significantly
> **Estimated effort:** 2 sessions

### Selection assistant (Auto Mark)

Moves from a separate bar to a **toolbar dropdown menu**:

```
[📋 Auto Mark ▼]
├── Select all except newest
├── Select all except oldest
├── Select all except largest
├── Select all except smallest
├── Select all except highest resolution (photos mode)
├── ──────────────
├── Select all in folder...
├── Select by extension...
├── ──────────────
├── Select all except first in group
├── Invert selection
└── Clear all selections
```

### Premium polish items

| Feature | Description |
|---------|-------------|
| Drag-and-drop folders | Drop from Windows Explorer onto folder panel or content area |
| Scan progress in taskbar | Windows taskbar progress bar via ITaskbarList3 COM |
| Window state persistence | Remember size, position, panel proportions, last folders |
| Keyboard shortcuts | Ctrl+O (add), Ctrl+Enter (search), Del (delete), Space (toggle), Ctrl+A (select all) |
| Undo delete toast | "12 files deleted. [Undo]" notification with 30-second window |
| Error log viewer | Menu → Help → View Errors — shows files that couldn't be read/hashed |
| Scan history | Menu → View → Scan History — lightweight dialog showing past scans |

### Deliverables

| File | Action | Description |
|------|--------|-------------|
| `ui/toolbar.py` | MODIFY | Auto Mark as dropdown menu |
| `ui/selection_bar.py` | DELETE | Replaced by toolbar dropdown |
| `ui/main_window.py` | MODIFY | Drag-drop, keyboard shortcuts, window state |
| `core/settings.py` | MODIFY | Persist window state + last folders |
| `ui/scan_history_dialog.py` | CREATE | Lightweight history viewer |

---

## 11. Phase 7 — VS Code Theme System Integration

> **Priority:** Lower — visual polish, all functionality must work first
> **Estimated effort:** 2 sessions

Integrate the theme system from `CEREBRO_V2_THEME_SYSTEM.md`:

1. Build `core/theme_engine.py`, `theme_schema.py`, `theme_loader.py`, `color_utils.py`
2. Create all 12 built-in theme JSON files
3. Refactor every widget to use `ThemeEngine.get().get_color(slot)` pattern
4. Add theme selector to Settings dialog
5. Build custom theme editor dialog
6. Test live switching across all themes

---

## 12. Complete Task Checklist

### Execution order (recommended)

```
Phase A  ──→  Phase B  ──→  Phase C  ──→  Phase D  ──→  Phase E
(critical     (nav bar      (left panel   (results      (preview
 bugs)         overhaul)     restructure)  build-out)    polish)
   │
   └──→ Can run in parallel after Phase A:
         Phase 4  (video/music engines)
         Phase 5  (empty folders / large files)
   │
   └──→ Requires Phases A-D complete:
         Phase 6  (selection assistant + polish)
   │
   └──→ Requires Phases A-E complete:
         Phase 7  (theme system)
```

### Master checklist

| # | Task | Phase | Status | Priority |
|---|------|-------|--------|----------|
| 1 | Wire Delete Selected → send2trash | A | ⬜ | CRITICAL |
| 2 | Build CheckTreeview widget | A | ⬜ | CRITICAL |
| 3 | Add Start Search button to toolbar | A | ⬜ | CRITICAL |
| 4 | Wire folder panel → orchestrator → results pipeline | A | ⬜ | CRITICAL |
| 5 | Rewrite toolbar with all Ashisoft buttons | B | ⬜ | HIGH |
| 6 | Rewrite mode tabs (icon + text, compact, page-switch) | B | ⬜ | HIGH |
| 7 | Move result filter tabs inside results area | B | ⬜ | HIGH |
| 8 | Wire mode tab switching to page-swap logic | B | ⬜ | HIGH |
| 9 | Rewrite left panel as tab-based (Folders/Protect) | C | ⬜ | HIGH |
| 10 | Mode-dependent scan settings in left panel | C | ⬜ | HIGH |
| 11 | Left panel collapse post-scan, expand pre-scan | C | ⬜ | HIGH |
| 12 | Build full results treeview with groups + checkboxes | D | ⬜ | HIGH |
| 13 | Build result type filter bar with counts | D | ⬜ | HIGH |
| 14 | Build empty state / getting-started view | D | ⬜ | HIGH |
| 15 | Build scanning state with progress | D | ⬜ | HIGH |
| 16 | Right-click context menu on results | D | ⬜ | MEDIUM |
| 17 | Rewrite preview panel (collapsed default, compact) | E | ⬜ | MEDIUM |
| 18 | Remove Keep A / Keep B buttons | E | ⬜ | MEDIUM |
| 19 | Context-sensitive preview (image vs file info) | E | ⬜ | MEDIUM |
| 20 | Build video dedup engine | 4 | ⬜ | NORMAL |
| 21 | Build music dedup engine | 4 | ⬜ | NORMAL |
| 22 | Video/music scan options in left panel | 4 | ⬜ | NORMAL |
| 23 | Build empty folder engine | 5 | ⬜ | NORMAL |
| 24 | Build large file engine | 5 | ⬜ | NORMAL |
| 25 | Auto Mark as toolbar dropdown (not separate bar) | 6 | ⬜ | NORMAL |
| 26 | Implement all 10 selection rules | 6 | ⬜ | NORMAL |
| 27 | Drag-and-drop folders from Explorer | 6 | ⬜ | NORMAL |
| 28 | Keyboard shortcuts | 6 | ⬜ | NORMAL |
| 29 | Window state persistence | 6 | ⬜ | NORMAL |
| 30 | Undo delete toast notification | 6 | ⬜ | NORMAL |
| 31 | Scan history dialog | 6 | ⬜ | NORMAL |
| 32 | Theme engine + schema + loader + color utils | 7 | ⬜ | LOWER |
| 33 | 12 built-in theme JSON files | 7 | ⬜ | LOWER |
| 34 | Refactor all widgets to use ThemeEngine | 7 | ⬜ | LOWER |
| 35 | Theme selector in Settings dialog | 7 | ⬜ | LOWER |
| 36 | Custom theme editor dialog | 7 | ⬜ | LOWER |

**Total: 36 tasks across 7 phases + 4 remaining engine phases**

---

## 13. Story status snapshot (April 2026 backlog triage)

This section records which backlog IDs are **addressed in code** vs still **open**, so Phase C–E items are not duplicated.

### Closed or largely satisfied (do not re-scope as “HIGH” unless adding new scope)

| ID | Story | Status |
|----|--------|--------|
| **UI-C1** | Left panel tab-based (Folders / Protect) | **Done** — see `cerebro/ui/folder_panel.py` (`TabView`, Folders + Protect tabs). Further work is polish (collapse behavior, task #11), not “add tabs”. |
| **UI-D1** | Empty / getting-started in results | **Done** — `ResultsPanel` empty state: hero, copy, Add Folders / Search Now, numbered steps (`results_panel.py`). |
| **UI-D2** | Scanning state + progress | **Done** — scanning frame, progress bar, current file / count (`results_panel.py`, `update_scan_progress`). |
| **UI-E1** | Preview collapsed by default | **Done** — `PreviewPanel` uses `_expanded = False`; expand when a file is loaded (`preview_panel.py`, `main_window._on_file_selected`). |
| **UI-B2 (filters)** | Result type filters | **UI + behavior** — segmented filters filter the tree by extension; counts unchanged (`results_panel._filtered_groups` / `_set_filter`). |

### Still open (checklist / future work)

| Area | Notes |
|------|--------|
| **Mode tab → page swap** (checklist #8) | Mode tabs switch engine mode; full “page swap” layout may still differ from Ashisoft. |
| **Left panel collapse** (task #11) | Not implemented as automatic post-scan behavior. |
| **Dedicated Settings window** | Stub `messagebox` only; full dialog + theme (Phase 7) still pending. |
| **Engines** | Video, music, empty folders, large files (checklist #20–24) as before. |

### Known placeholders (tracked in code / UX)

| Item | Where |
|------|--------|
| Toolbar **Remove** removes **last** scan folder (no list selection) | `main_window._on_remove_path` |
| **Settings** / **Help** | Info dialogs until real dialogs exist | `main_window._on_show_settings`, `_on_show_help` |
| **Scan options** | Passed from `FolderPanel.get_scan_options()` → `configure_scan` | `main_window._on_start_scan` |
| **Preview** | Loads on result row click/check via `PreviewPanel.load_file` | `main_window._on_file_selected` |

---

*End of UI overhaul plan. Start with Phase A — the app cannot function without delete wiring and a results treeview.*
