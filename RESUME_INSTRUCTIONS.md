# Resume Instructions - Cerebro v2 Refactoring

## Quick Resume Template

Copy and paste this when starting a new conversation:

```
I'm working on Cerebro v2 refactoring (Ashisoft Edition).

📁 Repository: C:\Users\S8633\silver-octo-pancake
📋 Implementation Plan: C:\Users\S8633\Downloads\CEREBRO_V2_IMPLEMENTATION_PLAN (1).md

=== CURRENT STATUS ===
Progress: Phase 0 ✅ | Phase 1 ✅ | Phase 2 ✅ | Phase 3 🔄 Next

Latest commit: 8138f29 Phase 1 Complete - Single-Window Shell Integration
Current phase: Phase 3 - Image Dedup Engine + Preview

=== TO RESUME ===
1. Read PHASE_X_PROGRESS.md for detailed status
2. Check git log for recent commits: git log --oneline -5
3. Read RESUME_INSTRUCTIONS.md for workflow

=== NEXT TASK ===
[Next specific task from progress file]
```

---

## Workflow Checklist

### After Completing Work

- [ ] **Test** - Verify changes work before committing
- [ ] **Commit** - Use descriptive commit message format:
  ```
  Phase X Complete - [Component Name]
  
  [Brief description of what was done]

  Files changed:
  - file1.py: change description
  - file2.py: change description

  Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
  ```
- [ ] **Push** - `git push origin main`
- [ ] **Pull** - `git pull origin main` (to sync remote changes)
- [ ] **Update Progress File** - Rename/create new phase progress file

---

## Phase Progress Files

| Phase | File | Status |
|-------|------|--------|
| Phase 0 | (included in Phase 1) | ✅ Complete |
| Phase 1 | `PHASE_1_PROGRESS.md` | ✅ Complete |
| Phase 2 | `PHASE_2_PROGRESS.md` | ✅ Complete |
| Phase 3 | `PHASE_3_PROGRESS.md` | 🔄 Next |
| Phase 4 | `PHASE_4_PROGRESS.md` | Pending |
| Phase 5 | `PHASE_5_PROGRESS.md` | Pending |
| Phase 6 | `PHASE_6_PROGRESS.md` | Pending |

---

## Git Commands Reference

### Check Status
```bash
git status
git log --oneline -5
```

### Commit Workflow
```bash
git add <files>
git commit -m "Phase X - [Description]"
git push origin main
```

### Sync with Remote
```bash
git pull origin main
# Resolve conflicts if any
git push origin main
```

### View History
```bash
git log --oneline --graph -10
git show HEAD
```

---

## Phase Overview

### Phase 0 ✅ - Foundation & Engine Layer
- `engines/base_engine.py` - ABC + dataclasses
- `engines/hash_cache.py` - SQLite cache
- `engines/orchestrator.py` - Engine dispatch
- `engines/file_dedup_engine.py` - File dedup engine
- `core/design_tokens.py` - Design tokens
- `core/performance.py` - Thread/process pools

### Phase 1 ✅ - Single-Window Shell
- `main_window.py` - Root window with all panels
- `toolbar.py` - Top toolbar with all buttons
- `mode_tabs.py` - 6-mode tab selector
- `folder_panel.py` - Left panel (folders + protect + options)
- `results_panel.py` - Center panel with CheckTreeview
- `preview_panel.py` - Bottom panel with dual canvases
- `selection_bar.py` - Selection assistant
- `status_bar.py` - Live status bar
- `settings_dialog.py` - Modal settings dialog
- `widgets/zoom_canvas.py` - Zoom/pan canvas
- `widgets/check_treeview.py` - Treeview with checkboxes

### Phase 2 ✅ - File Dedup Engine Wire-Up
- `main_window.py` - Root window with all panels
- `toolbar.py` - Top toolbar with all buttons
- `mode_tabs.py` - 6-mode tab selector
- `folder_panel.py` - Left panel (folders + protect + options)
- `results_panel.py` - Center panel with CheckTreeview
- `preview_panel.py` - Bottom panel with dual canvases
- `selection_bar.py` - Selection assistant
- `status_bar.py` - Live status bar
- `settings_dialog.py` - Modal settings dialog
- `widgets/zoom_canvas.py` - Zoom/pan canvas
- `widgets/check_treeview.py` - Treeview with checkboxes

### Phase 2 ✅ - File Dedup Engine (Wire-Up)
- Wire toolbar "Start Search" to orchestrator
- Wire progress callback to status bar
- Wire results to CheckTreeview
- Wire result selection to preview
- Wire "Delete Selected" to send2trash
- Wire results sub-filter tabs

### Phase 3 🔄 - Image Dedup Engine + Preview
- Wire toolbar "Start Search" to orchestrator
- Wire progress callback to status bar
- Wire results to CheckTreeview
- Wire result selection to preview
- Wire "Delete Selected" to send2trash
- Wire results sub-filter tabs

### Phase 3 ⏸ - Image Dedup Engine + Preview
- `engines/image_dedup_engine.py` - pHash + dHash pipeline
- Preview panel enhancements (resolution, format badge, diff)

### Phase 4 ⏸ - Video & Music Engines
- `engines/video_dedup_engine.py` - FFmpeg frame extraction
- `engines/music_dedup_engine.py` - ID3 tag fuzzy matching

### Phase 5 ⏸ - Utility Tools
- `engines/empty_folder_engine.py` - Empty folder finder
- `engines/large_file_engine.py` - Size-ranked file listing

### Phase 6 ⏸ - Selection Assistant & Polish
- 8+ selection rules implementation
- Premium polish (animations, drag-drop, undo delete, etc.)

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `RESUME_INSTRUCTIONS.md` | This file - how to resume work |
| `PHASE_X_PROGRESS.md` | Detailed progress for current phase |
| `CEREBRO_V2_IMPLEMENTATION_PLAN.md` | Full architecture and requirements |
| `cerebro/engines/` | All scan engines |
| `cerebro/v2/core/` | Core utilities (tokens, performance) |
| `cerebro/v2/ui/` | All UI components |

---

## Context Preservation Strategy

When the token limit is hit (3000s):

1. **Commit first** - Save all current work
2. **Push to remote** - Ensure backup
3. **Update progress file** - Document exactly where you stopped
4. **Note the task** - Write down what was being worked on

Example progress file entry:
```
## Last Work Session (2026-04-01)

### What Was Done
- Implemented file deletion flow in main_window.py
- Added confirmation dialog with reclaimable space calculation

### What's Left
- Hook up actual send2trash.send2trash() call (line 465)
- Test delete functionality

### Files Modified
- cerebro/v2/ui/main_window.py (lines 445-476)
- cerebro/v2/ui/selection_bar.py (wired delete button)
```

---

## Dependencies

```bash
pip install customtkinter Pillow imagehash numpy scipy pillow-heif rawpy mutagen send2trash windnd blake3
```

System: FFmpeg (optional, for video mode)

---

## Testing Quick Reference

```bash
# Run main window
python -m cerebro.v2.ui.main_window

# Test imports
python -c "from cerebro.v2.ui.main_window import MainWindow; print('OK')"

# Syntax check
python -m py_compile cerebro/v2/ui/main_window.py
```

---

*Last Updated: 2026-04-01*
