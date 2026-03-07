# Scan Result Store + Query-Backed Review — Architecture Design (Read-Only)

**Goal:** Eliminate the full in-memory scan result handoff and make Review load/query duplicate groups by `scan_id` from a persistent store.

**Status:** Design only. No code changes.

---

## 1. Current flow (summary)

| Step | Component | What happens |
|------|------------|--------------|
| 1 | **FastPipeline.run_fast_scan** | Builds `groups = [{"hash", "paths", "count"}, ...]` in memory; returns `{"ok", "groups", "stats"}`. |
| 2 | **FastScanWorker.run** | Calls `run_scan()` or `_run_with_scanner()`; gets full result; builds `payload` with `payload.setdefault("groups", payload.get("groups") or [])`; `self.finished.emit(payload)`. |
| 3 | **LiveScanController._on_completed** | Receives `result`; `payload = dict(result)`; `payload.setdefault("scan_id", self._scan_id)`; emits `bus.scan_completed.emit(payload)` and `self.scan_completed.emit(payload)`. Full payload (including `groups`) on both. |
| 4 | **MainWindow._on_scan_completed** | Receives `result`; navigates to review; `review.load_scan_result(result)`; `hist.ingest_scan_result(result)`; sets last_scan_summary from result. |
| 5 | **ReviewPage.load_scan_result** | `self._result = dict(result)`; `groups_raw = self._result.get("groups") or []`; `_all_groups = [extract_group_data(g, i) for ...]`; `_keep_states` from all groups; `_populate_group_list()`; `_update_display()`; `_update_stats()`. |

**Contract today:** “Scan completed” = “here is the whole scan universe” (full `groups` list). Worker, bus, MainWindow, and Review all see the same heavy payload.

---

## 2. Proposed scan result store schema

**Location:** Dedicated store under `~/.cerebro/` (e.g. `~/.cerebro/scan_results/` or a single SQLite DB `scan_results.db`). Keep separate from `HistoryStore` (deletion audit) and hash cache.

**Schema (SQLite):**

```sql
-- One row per scan (metadata only; no group data here).
CREATE TABLE scans (
    scan_id TEXT PRIMARY KEY,
    scan_root TEXT NOT NULL,
    scan_name TEXT,
    status TEXT NOT NULL DEFAULT 'completed',  -- 'completed' | 'cancelled' | 'failed'
    files_scanned INTEGER NOT NULL DEFAULT 0,
    groups_count INTEGER NOT NULL DEFAULT 0,
    total_size INTEGER NOT NULL DEFAULT 0,
    scan_duration_seconds REAL,
    created_at REAL NOT NULL,
    config_json TEXT,  -- optional: scanner_tier, media_type, etc.
    UNIQUE(scan_id)
);

-- One row per duplicate group (no file paths here).
CREATE TABLE duplicate_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id TEXT NOT NULL,
    group_index INTEGER NOT NULL,  -- 0-based index in this scan
    duplicate_hash TEXT,           -- quick hash if available
    file_count INTEGER NOT NULL,
    total_bytes INTEGER NOT NULL DEFAULT 0,
    category TEXT,                -- 'Images' | 'Videos' | etc. (derived from first file)
    FOREIGN KEY (scan_id) REFERENCES scans(scan_id) ON DELETE CASCADE,
    UNIQUE(scan_id, group_index)
);
CREATE INDEX idx_duplicate_groups_scan ON duplicate_groups(scan_id);
CREATE INDEX idx_duplicate_groups_scan_category ON duplicate_groups(scan_id, category);

-- One row per file in a group (path and order).
CREATE TABLE group_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id TEXT NOT NULL,
    group_index INTEGER NOT NULL,
    file_index INTEGER NOT NULL,   -- 0 = first file in group, etc.
    path TEXT NOT NULL,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (scan_id) REFERENCES scans(scan_id) ON DELETE CASCADE,
    UNIQUE(scan_id, group_index, file_index)
);
CREATE INDEX idx_group_files_scan_group ON group_files(scan_id, group_index);

-- Optional: keep/delete selection state (so Review can restore after reload).
CREATE TABLE selection_state (
    scan_id TEXT NOT NULL,
    group_index INTEGER NOT NULL,
    path TEXT NOT NULL,
    keep INTEGER NOT NULL DEFAULT 1,  -- 1 = keep, 0 = mark for delete
    updated_at REAL,
    PRIMARY KEY (scan_id, group_index, path),
    FOREIGN KEY (scan_id) REFERENCES scans(scan_id) ON DELETE CASCADE
);
CREATE INDEX idx_selection_state_scan ON selection_state(scan_id);
```

**Design notes:**

- **scans:** Single source of truth for “what scan ran”; summary counts and scope. No `groups` blob.
- **duplicate_groups:** One row per group; `group_index` is stable for the life of the scan. `category` supports filter-by-type without loading paths.
- **group_files:** Normalized paths; supports “fetch paths for group_id” and “fetch group window” (e.g. join with duplicate_groups and paginate by `group_index`).
- **selection_state:** Optional; allows “load by scan_id” and restore checkboxes without holding full `_keep_states` in memory. Can be added in a later phase.

---

## 3. New completion contract

**Principle:** The worker emits “scan finished” + identity + summary. It does **not** emit the full group list.

**Light payload (what is emitted on completion):**

```python
# Emitted by LiveScanController to bus and scan_completed (no full "groups" key).
{
    "scan_id": str,
    "scan_root": str,
    "scan_name": str,
    "status": "completed" | "cancelled" | "failed",
    "files_scanned": int,
    "groups_count": int,
    "total_size": int,
    "scan_duration": float,
    "result_store_path": str | None,  # path to DB file or "" if in-memory fallback
    # Optional: keep for backward compat during migration
    # "groups": []  # MUST be omitted or empty at scale
}
```

**Contract rules:**

1. **Worker** (or pipeline) must write the full result to the scan result store **before** signalling completion. The worker (or a helper it calls) is responsible for persisting `scans` + `duplicate_groups` + `group_files` for the current `scan_id`.
2. **Controller** builds the light payload from the full result (or from pipeline callback) and emits only that. It must **not** attach `result["groups"]` to the payload when a store was used.
3. **Bus / MainWindow** treat the completion event as “scan finished; here is scan_id and summary”. They do not expect `payload["groups"]`.
4. **Review** receives the light payload; it calls `load_scan_result(scan_id, summary)` (or equivalent) and loads data from the store by `scan_id`. History and Start page use the same light payload for ingest and recent-scan summary.

**Backward compatibility during migration:** If “result_store_path” is missing or empty, Review can fall back to “load from payload['groups'] if present” so old code paths still work until all callers are updated.

---

## 4. Review query model

Review stops holding `_result["groups"]`, `_all_groups`, and full `_keep_states` in memory. Instead it talks to the store by `scan_id`.

**Required operations (store interface):**

| Operation | Purpose |
|-----------|--------|
| `get_scan_summary(scan_id) -> dict \| None` | Metadata for header/summary (files_scanned, groups_count, scan_root, status). |
| `get_group_window(scan_id, offset, limit) -> List[GroupRow]` | Paginated groups; each row has group_index, file_count, total_bytes, category (and optionally hash). No paths. |
| `get_group_details(scan_id, group_index) -> GroupDetails` | Paths and metadata for one group (for center pane, file table, preview). |
| `get_group_count(scan_id, category=None) -> int` | Total groups (optionally filtered by category) for virtual list and filters. |
| `get_categories(scan_id) -> List[str]` | Distinct categories for filter dropdown. |
| `set_selection_state(scan_id, group_index, path, keep: bool)` | Optional; persist keep/delete per path. |
| `get_selection_state(scan_id) -> Dict[group_index, Dict[path, bool]]` | Optional; restore checkboxes. |

**GroupRow (minimal):** `group_index`, `file_count`, `total_bytes`, `category` (and optionally `duplicate_hash`). No path list.

**GroupDetails:** `group_index`, `paths: List[str]`, `file_count`, `total_bytes`, `category`, `similarity` (if stored).

**Review flow with store:**

1. **load_scan_result(payload)**  
   - If payload has `result_store_path` / `scan_id` and store has data for it: set `_current_scan_id`, `_scan_summary` from payload or `get_scan_summary(scan_id)`. Do **not** set `_all_groups` or load all groups into memory.  
   - If payload has `groups` (fallback): keep current behavior for backward compat.

2. **Virtual list (left pane)**  
   - Model asks store: `get_group_count(scan_id, category=_current_filter)` for total; `get_group_window(scan_id, offset, limit)` for the current window. Model holds only the current window of GroupRow (e.g. 50–100 rows), not all groups.

3. **Selection / display**  
   - When user selects a row (group_index): call `get_group_details(scan_id, group_index)` to get paths; populate center pane and file table. Optionally cache last N group details to avoid repeated DB reads.

4. **Filtering**  
   - Filter dropdown: `get_categories(scan_id)`. On filter change: update `_current_filter`; model refreshes count and window with `get_group_count(scan_id, category)` and `get_group_window(..., category=...)`. Store must support filtering by category (index on `duplicate_groups(scan_id, category)`).

5. **Keep/delete state**  
   - Option A (minimal): Keep `_keep_states` in memory but only for **loaded** groups (current window + recently viewed). Evict when scrolling away.  
   - Option B: Persist to `selection_state` table; on load restore via `get_selection_state(scan_id)`; on toggle update store and in-memory cache.

6. **Delete plan**  
   - Build from current selection: for each group in “current window” or “all groups” (via iterator or chunked fetch), if any path is marked delete, add to delete list. So we iterate over group_ids we care about and fetch only those group details (or use selection_state + group_files) to build the plan. No need to hold full `_all_groups` in memory.

---

## 5. Minimum implementation order (smallest safe migration)

**Phase M1 — Store + write path (no UI change yet)**  
- Add `cerebro/scan_result_store.py` (or under `cerebro/history/`): open SQLite DB, implement `write_scan_result(scan_id, scan_root, groups, stats, ...)` that fills `scans`, `duplicate_groups`, `group_files`.  
- In **FastPipeline.run_fast_scan** (or in **FastScanWorker** after receiving result): before returning/emitting, call store to write the result for this `scan_id`. Decide scan_id at start of scan (worker already has it) and pass it through.  
- Keep emitting the **full** payload from worker/controller for now (so existing UI still works).  
- **Acceptance:** After a scan, DB file exists and contains correct rows for that scan_id.

**Phase M2 — Light payload + Review fallback**  
- **LiveScanController._on_completed:** When a result store was used, build light payload only (no `groups`); set `result_store_path` to the DB path (or a well-known path + scan_id). Emit light payload.  
- **MainWindow._on_scan_completed:** Pass payload to Review unchanged (payload may be light or legacy).  
- **ReviewPage.load_scan_result:** If payload has `result_store_path` (or store has data for `payload["scan_id"]`), then load summary from store; set `_current_scan_id`; use store for `get_group_count` and `get_group_window`; do **not** populate `_all_groups`. If payload has non-empty `groups`, use current in-memory path (fallback).  
- **Acceptance:** With store enabled, Review shows groups from store; with store disabled or missing, Review still works from payload.

**Phase M3 — Review query-backed list**  
- Replace in-memory `_all_groups` / `_filtered_groups` with store-backed model: total count from `get_group_count(scan_id, category)`; window from `get_group_window(scan_id, offset, limit)`.  
- On row select: `get_group_details(scan_id, group_index)` to fill center/right panes.  
- Filter dropdown: `get_categories(scan_id)`; filter change triggers new count + window.  
- **Acceptance:** Review works for large scans without loading all groups into memory; scrolling and filter work via store.

**Phase M4 — Selection state (optional)**  
- Add `selection_state` table and get/set in store.  
- Review: on toggle keep/delete, update store; on load, restore from store. Optionally keep small in-memory cache for current window.  
- **Acceptance:** Selection survives reload or can be reconstructed from store.

**Phase M5 — Remove legacy path**  
- Once all callers use the store, stop emitting `groups` on the bus; remove fallback in Review that reads from `payload["groups"]`. Worker never attaches full groups to payload.

---

## 6. What can remain unchanged

- **Deletion execution path:** `CerebroPipeline.build_delete_plan` and `execute_delete_plan`, `PipelineCleanupWorker`, `DeletionResult`, MainWindow cleanup handling — unchanged. Only the **shape** of what Review sends (groups with keep/delete) can be built from store queries instead of from `_all_groups`.
- **HistoryStore (deletion audit):** `record_deletion`, `get_deletion_history`, `DeletionAuditRecord` — unchanged. Audit still keyed by scan_id and records counts; no need to store duplicate groups in HistoryStore.
- **Hash cache:** Stays as-is; it is for hash reuse, not for scan result storage.
- **Resume payload:** Can still store `scan_id` and config; no need to store full groups in resume.
- **Start page / Mission Control:** Consume light payload (scan_id, groups_count, scan_root) for recent scan summary; no change to contract except payload is light.
- **History page ingest:** `ingest_scan_result` can take light payload (scan_id, groups_count, root, etc.); no `groups` array needed.

---

## 7. File-by-file change plan (high level)

| File | Change (conceptual) |
|------|---------------------|
| **New: `cerebro/scan_result_store.py`** | Implement store: schema creation, `write_scan_result(scan_id, root, groups, stats)`, `get_scan_summary`, `get_group_window`, `get_group_details`, `get_group_count`, `get_categories`, optional selection_state get/set. |
| **`cerebro/engine/pipeline/fast_pipeline.py`** | After building `groups`, either return as today and let worker write store, or accept a `scan_id` and callback/store and write inside pipeline. Prefer worker writes store so pipeline stays engine-only. |
| **`cerebro/workers/fast_scan_worker.py`** | After `run_scan()` or _run_with_scanner: if store is enabled, call `store.write_scan_result(scan_id, ..., groups, stats)`; build light payload; emit light payload. Else emit full payload (migration). |
| **`cerebro/ui/controllers/live_scan_controller.py`** | In `_on_completed`: if result came from store-backed run, build light payload (scan_id, summary, result_store_path), do not attach `result["groups"]`; emit. Otherwise emit full payload for fallback. |
| **`cerebro/ui/main_window.py`** | `_on_scan_completed`: pass payload to Review and History as-is (no change to call sites; payload shape changes). |
| **`cerebro/ui/pages/review_page.py`** | `load_scan_result(payload)`: if light payload and store has scan_id, set _current_scan_id, load summary, use store for count/window/details; replace _all_groups/_filtered_groups usage with store-backed model. Add fetch_group_details(scan_id, group_index) for center pane. Filter and delete-plan build from store. Keep fallback when payload contains `groups`. |
| **`cerebro/ui/pages/history_page.py`** | `ingest_scan_result`: use payload["groups_count"] (or len(payload["groups"]) if present) for display; no dependency on full groups. |
| **Config / env** | Optional: config or env to enable/disable store (e.g. `CEREBRO_USE_SCAN_RESULT_STORE=1` or settings flag) so migration can be toggled. |

---

## 8. Migration phases (summary)

| Phase | Description | Risk |
|-------|-------------|------|
| **M1** | Add store; write after every scan; keep emitting full payload | Low; UI unchanged. |
| **M2** | Emit light payload when store used; Review reads from store when possible, else from payload | Medium; must handle both payload shapes. |
| **M3** | Review fully query-backed; no in-memory _all_groups for store-backed scans | Medium; list model and filter logic change. |
| **M4** | Optional selection_state persistence | Low. |
| **M5** | Remove full payload from bus; worker never sends groups | Low; cleanup. |

---

## 9. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| **Store write failure** | On write error, fall back to emitting full payload so Review still works; log and optionally retry. |
| **DB size** | One DB per scan or one DB with many scans; add retention (e.g. keep last N scans or delete scans older than X days). |
| **Concurrent scans** | Use distinct scan_id per run; store writes keyed by scan_id; no cross-scan conflict. |
| **Review opens before write completes** | Controller emits completion only after store write returns; worker or controller must sequence “write then emit”. |
| **Backward compat** | Review and History accept both light and legacy payloads until M5. |
| **Performance of get_group_window** | Index on (scan_id, group_index); use LIMIT/OFFSET or keyset pagination; keep window size small (e.g. 100). |
| **Category filter** | Index on (scan_id, category); precompute category when writing group (e.g. from first file path). |

---

## 10. Alignment with “UI truth” and product direction

- **Scan truth:** Store holds status, files_scanned, groups_count, scope (scan_root). UI can show “Scan completed • 66,100 files • 124 duplicate groups” from summary only.  
- **Result truth:** Each group row can expose match type (e.g. hash) and category; group_details can expose paths and sizes; optional “confidence” or “source” fields can be added to schema later.  
- **Deletion truth:** Delete plan is built from current selection (store or in-memory cache); pipeline and audit trail unchanged.  
- **Empty-state truth:** Review can distinguish “no scan loaded”, “scan has 0 groups”, “filter has 0 groups” from store counts and load state.

This design does not implement Simple vs Advanced UI or the default workflow; it only provides the data layer so that “query-backed UX” and “state-explicit UI” can be built on top without the current full-result handoff.

---

*Document generated for CEREBRO v6; read-only design. No code modified.*
