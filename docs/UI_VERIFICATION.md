# UI verification checklist (v6 alignment)

Use this after UI changes to confirm flows and performance.

## 1. End-to-end flows

- [ ] **Scan → Review**
  - Pick folder on Scan page, choose strategy (Simple/Advanced/Turbo or Experimental), Start Scan.
  - When complete, app navigates to Review; groups and files appear.
- [ ] **Review → Delete**
  - Mark some files for deletion, click Delete; confirm (Recycle Bin or Permanent).
  - Progress dialog shows; when done, result banner shows "Deleted N files" (and "M failed" if any).
  - "View failures" opens if there were failures.
- [ ] **History**
  - History page shows deletion audits with timestamp, mode, deleted/failed, groups, strategy.
  - Export (JSON/CSV) works.
- [ ] **Audit**
  - Audit → Deletion History runs and shows scan_id, strategy, groups, deleted, failed per run.
- [ ] **Hub**
  - Hub → Engine & Environment shows environment, cache, ScanEngine, optional deps, experimental toggle.
- [ ] **Start (Mission Control)**
  - Dashboard shows active strategy; after a scan, "Recent scan" shows group count and root.
  - Quick launch: Start Scan, Review, History, Themes, Settings navigate correctly.
  - "Resume last scan" is enabled after cancelling a scan; clicking it opens Scan with folder/options restored.

## 2. Performance (large scans)

- [ ] Run a scan that produces hundreds of duplicate groups.
- [ ] Review left list scrolls smoothly (virtualized list).
- [ ] Thumbnails load without freezing (async; "…" then image).
- [ ] Deletion progress updates without blocking the window.

## 3. Theme and settings

- [ ] Change theme (Themes page); Review/Hub/Audit use token colors (no hardcoded hex).
- [ ] Settings → Cleanup: default deletion mode; Settings → Advanced: default scanner tier, experimental toggle.
- [ ] Confirm dialog respects default deletion mode from Settings.

## 4. Quick smoke test (no GUI)

From repo root:

```bash
python -c "
from cerebro.scanners import CORE_TIERS, get_scanner
from cerebro.history.store import HistoryStore
from cerebro.ui.state_bus import get_state_bus
bus = get_state_bus()
bus.set_last_scan_summary({'groups': 5, 'root': '/tmp', 'scan_id': 'test'})
summary = bus.get_last_scan_summary()
assert summary.get('groups') == 5
store = HistoryStore()
p = store.get_latest_resume_payload()
print('CORE_TIERS', CORE_TIERS, 'get_scanner(turbo)', get_scanner('turbo') is not None)
print('Resume payload:', p)
print('OK')
"
```
