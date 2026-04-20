# Cerebro Scan Path Audit
*Generated: Phase 1 post-v1 audit*

## Active Scan Paths

### Path A — PRIMARY (default production path)
- **Entry**: `cerebro/workers/fast_scan_worker.py` `FastScanWorker._run_optimized_scan()`
- **Via**: `cerebro/core/scanner_adapter.py` `OptimizedScannerAdapter.scan()`
- **Core**: `cerebro/core/scanners/turbo_scanner.py` `TurboScanner.scan()`
- **Trigger**: `scanner_tier` in `{"turbo", "ultra", "quantum"}` (default: `"turbo"`)
- **Canonical dedup**: NONE
- **Cache-backed**: YES (`HashCache` SQLite at `~/.cerebro/cache/hash_cache.sqlite`)
- **Logger**: `get_logger(__name__)` via `cerebro.services.logger` — CEREBRO handler ✓

### Path B — LEGACY FALLBACK
- **Entry**: `cerebro/workers/fast_scan_worker.py` `FastScanWorker.run()`
- **Core**: `cerebro/core/fast_pipeline.py` `FastPipeline.run_fast_scan()`
- **Trigger**: `scanner_tier` is any value NOT in `{"turbo", "ultra", "quantum"}`
- **Canonical dedup**: NONE
- **Cache-backed**: YES (conditional on `cache_path` being set)
- **Logger**: none in original — added `get_logger(__name__)` in Phase 1

### Path C — ENGINE MODE
- **Entry**: `cerebro/engines/turbo_file_engine.py` `TurboFileEngine._do_scan()`
- **Core**: `cerebro/core/scanners/turbo_scanner.py` `TurboScanner.scan()` (direct)
- **Trigger**: `ScanOrchestrator.start_scan()` with `mode="files"` (registered default)
- **Canonical dedup**: NONE
- **Cache-backed**: YES (same `HashCache` as Path A)
- **Logger**: `logging.getLogger(__name__)` — bypasses CEREBRO file handler

### Path D — CLASSIC ENGINE
- **Entry**: `cerebro/engines/file_dedup_engine.py` `FileDedupEngine._run_scan()`
- **Trigger**: `ScanOrchestrator.start_scan()` with `mode="files_classic"`
- **Canonical dedup**: NONE
- **Cache-backed**: YES (own `HashCache` from `cerebro.engines.hash_cache`)
- **Logger**: `logging.getLogger(__name__)` at module bottom — bypasses CEREBRO file handler

### Convenience Wrappers
- `cerebro/core/scanners/turbo_scanner.py` `quick_scan()` → TurboScanner.scan() — Path A core
- `cerebro/core/scanners/turbo_scanner.py` `incremental_scan()` → TurboScanner.scan() — Path A core

---

## Dead Paths

### Path E — DEAD
- **Entry**: `cerebro/workers/scan_worker.py` `ScanWorker.execute()`
- **Calls**: `CerebroPipeline().run(request, ...)` — `CerebroPipeline` in `cerebro/core/pipeline.py`
  has no `.run()` method (it is a **delete pipeline**, not a scan pipeline)
- **Never instantiated**: No UI or controller code creates `ScanWorker`
- **Status**: DEAD — would raise `AttributeError` if ever called

---

## Bug 1 Surface: Canonical-Path False Positives

All four active paths group files by size before hashing. None apply canonical-path
deduplication. On Windows, paths to the same physical file can appear as distinct strings
via: NTFS hardlinks, directory junctions, 8.3 short-name aliases, or Unicode
normalization variants. When two such paths fall in the same size group, they hash
identically and are incorrectly reported as duplicates.

**Fix target (Phase 2)**: apply canonical dedup at the size-grouping chokepoint in
each active path using `os.path.normcase(os.path.realpath(p))` +
`unicodedata.normalize("NFC", ...)`.

---

## Phase 1 Instrumentation Added

DIAG log markers added to all active paths at INFO level:
- `[DIAG:DISCOVERY]` — file count actually passed downstream, root(s), filters
- `[DIAG:REDUCE]` — count-in / count-out at each size/hash reduction step
- `[DIAG:REDUCE] canonical-path collision` / `inode collision` — per `_diagnose_pair()`
- `[DIAG:SUMMARY]` — final totals: discovered, candidates, groups, elapsed, cache hit%
