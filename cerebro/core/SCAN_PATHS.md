# Cerebro Scan Path Audit
*Last revised: post-v1 audit, Cut 2 ("single entrance") landed*

## One Entrance

All file scans enter through **`ScanOrchestrator.start_scan(mode, folders, ...)`**
(`cerebro/engines/orchestrator.py`). The orchestrator dispatches to a registered
engine keyed by `mode`. The only file-duplicate scan core that ships is
**`TurboScanner.scan()`** (`cerebro/core/scanners/turbo_scanner.py`), reached via
the `TurboFileEngine` adapter.

```
UI (scan_page / main_window_controllers / audit.py)
     │
     ▼
ScanOrchestrator.start_scan(mode=…)
     │
     ├─ mode="files"          → TurboFileEngine   → TurboScanner.scan()
     ├─ mode="files_classic"  → FileDedupEngine   → own 4-stage pipeline  (Path D — scheduled for Cut 3)
     ├─ mode="photos"         → ImageDedupEngine
     ├─ mode="videos"         → VideoDedupEngine
     ├─ mode="music"          → MusicDedupEngine
     ├─ mode="empty_folders"  → EmptyFolderEngine
     └─ mode="large_files"    → LargeFileEngine
```

## What was removed in Cut 2

Legacy PyQt-era scan surface, confirmed dead by grep (no runtime caller):

| Removed file                           | Role                                      |
|----------------------------------------|-------------------------------------------|
| `cerebro/workers/fast_scan_worker.py`  | `FastScanWorker(QThread)` — Paths A + B  |
| `cerebro/core/fast_pipeline.py`        | `FastPipeline` — Path B legacy core       |
| `cerebro/workers/scan_worker.py`       | `ScanWorker(BaseWorker)` — Path E (dead) |
| `cerebro/workers/media_scan_worker.py` | `MediaScanWorker(QThread)` — no caller   |
| `cerebro/core/scanner_adapter.py`      | `OptimizedScannerAdapter` — only FastScanWorker consumed it |
| `cerebro/core/grouping.py`             | `SizeGrouping` — confirmed dead           |
| `sanity/stress_scan.py`                | Only user of FastScanWorker               |

Net deletion: ~1,500 lines.

## What remains

- **Path A/C core**: `cerebro/core/scanners/turbo_scanner.py` — the single
  file-scan engine that ships.
- **Path D**: `cerebro/engines/file_dedup_engine.py` — independent classic
  implementation, still registered as `files_classic`. Scheduled for removal in
  Cut 3 (see "one entrance" plan).

## Phase 1 instrumentation still in effect

DIAG log markers remain at INFO level on all live paths:

- `[DIAG:DISCOVERY]` — file count actually passed downstream, root(s), filters
- `[DIAG:REDUCE]`    — count-in / count-out at each reduction step
- `[DIAG:PAIR]`      — per-pair canonical-path / inode collision detection (capped at 8 per scan)
- `[DIAG:SUMMARY]`   — final totals
- `[DIAG:GUARD]`     — `_assert_no_self_duplicates` regression guard output
- `[DIAG:EMIT]`      — singleton-group filter at the emit step
- `[ROOT_DEDUP]`     — root-overlap collapse (Phase 2a fix)

## Phase 1 waivers (still in force)

- **Waiver 1A** — `[DIAG:SUMMARY]` lacks `groups_dropped_self_dup` and `scan_type`
  fields. Superseded by `[DIAG:GUARD]`. Accepted.
- **Waiver 1B** — `_diagnose_pair()` capped at 8 invocations per scan to prevent
  log flooding. Accepted.
- **Waiver 1C** — Phase 1 sample log used the `jhjl` test tree; production
  evidence is documented in `docs/bug-investigations/bug1-canonical-path-dedup.md`.

## Bug 1 canonical-path dedup

Fixed in Phase 2a via `cerebro/core/root_dedup.py::dedupe_roots()` at the root
layer, plus the `_assert_no_self_duplicates` guard in
`cerebro/core/group_invariants.py` at the group layer. Both guards are live on
Paths A/C (TurboScanner) and Path D (FileDedupEngine). Full evidence and
waivers in `docs/bug-investigations/bug1-canonical-path-dedup.md`.
