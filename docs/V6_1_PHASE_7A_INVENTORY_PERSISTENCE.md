# CEREBRO v6.1 — Phase 7A: Inventory Schema + Persistence

**Branch:** `v6.1-scale-foundation`  
**Phase:** 7A — Epic B (Global Inventory + Device-Aware Matching)  
**Reference:** `V6_1_INVENTORY_SCHEMA.md`, `V6_1_SCALE_FOUNDATION_PLAN.md`

---

## 1. Objective

Add the persistent inventory DB with `devices` and `inventory_files` tables. First scan populates inventory; second scan reuses metadata safely. Unchanged files skip redundant work where possible.

---

## 2. Scope (Phase 7A Only)

| In scope | Out of scope |
|----------|--------------|
| `cerebro/services/inventory_db.py` (new) | Global matching (Phase 7B) |
| devices + inventory_files schema | Device offline detection (Phase 7C) |
| Device identity (basic) | Review UI labels |
| Populate on scan completion | Match scope config |
| Unchanged/new/changed classification | Delete scope changes |

---

## 3. Schema (from V6_1_INVENTORY_SCHEMA.md)

### 3.1 Devices table

```sql
CREATE TABLE devices (
    device_id TEXT PRIMARY KEY,
    device_label TEXT NOT NULL,
    device_type TEXT NOT NULL,  -- 'internal' | 'removable' | 'network'
    root_path TEXT NOT NULL UNIQUE,
    last_seen_timestamp REAL,
    is_online INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    updated_at REAL
);
```

### 3.2 Inventory files table

```sql
CREATE TABLE inventory_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    path TEXT NOT NULL,
    relative_path TEXT,
    size_bytes INTEGER NOT NULL,
    mtime_ns INTEGER NOT NULL,
    quick_hash TEXT,
    full_hash TEXT,
    last_seen_scan_id TEXT,
    last_seen_timestamp REAL NOT NULL,
    is_present INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
    UNIQUE(device_id, path)
);
```

### 3.3 Scan-inventory links (optional, Phase 7A)

```sql
CREATE TABLE scan_inventory_links (
    scan_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    files_added INTEGER NOT NULL DEFAULT 0,
    files_updated INTEGER NOT NULL DEFAULT 0,
    files_unchanged INTEGER NOT NULL DEFAULT 0,
    files_removed INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (scan_id, device_id)
);
```

---

## 4. Implementation Plan

### 4.1 New module: `cerebro/services/inventory_db.py`

**Class:** `InventoryDB`

**Location:** `~/.cerebro/inventory.db` (or configurable)

**Methods:**

| Method | Purpose |
|--------|---------|
| `ensure_schema(conn)` | Create tables if not exist |
| `get_or_create_device(root_path, label?, type?) -> device_id` | Resolve device_id for root; create device row if new |
| `upsert_file(device_id, path, size, mtime_ns, quick_hash?, last_seen_scan_id, last_seen_ts) -> str` | Insert or update; return classification: `unchanged` \| `new` \| `changed` |
| `get_file(device_id, path) -> row \| None` | Lookup for classification |
| `mark_device_online(device_id)` | Set is_online=1, last_seen_timestamp |
| `mark_device_offline(device_id)` | Set is_online=0 (Phase 7C) |
| `record_scan_link(scan_id, device_id, added, updated, unchanged, removed)` | Optional stats |

### 4.2 Device identity (Phase 7A — minimal)

**Phase 7A:** Use path-based fallback only.

```python
def _device_id_for_root(root_path: str) -> str:
    canonical = os.path.normpath(os.path.abspath(root_path))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]
```

**Phase 7C:** Add platform-specific volume UUID. For 7A, path hash is sufficient.

### 4.3 Integration point: pipeline / worker

**When:** After scan completes, before or alongside result-store write.

**Flow:**

1. Worker has `scan_id`, `scan_root`, `groups`, `stats`.
2. For each file in the scan (we have this from pipeline — but pipeline returns groups, not full file list). **Gap:** Pipeline doesn't return the full discovered file list; it returns groups. To populate inventory, we need the full list of discovered files with their metadata.

**Options:**

- **A:** Pipeline returns `files_discovered: List[FastFileInfo]` in stats (or a separate key). Memory: full list again. Conflicts with chunking goal.
- **B:** Pipeline writes inventory incrementally during scan. As each chunk is processed, pipeline (or a callback) upserts to inventory. No full list in memory.
- **C:** Pipeline returns a path to a temp file or stream of (path, size, mtime, hash) that worker can iterate. Complex.
- **D:** Phase 7A — only populate inventory for files that are **in duplicate groups**. That's a subset. We have those in `groups`. So we can upsert each path in each group. We won't have unchanged/new/changed for non-duplicate files, but we'll have inventory for duplicate files. Partial but useful for 7B (matching).
- **E:** Add a separate "inventory update" pass. After scan, re-walk the root (or use a cached list). Two passes. Heavy.

**Recommendation for 7A:** **Option B** — pipeline writes to inventory during scan. Add an optional `inventory_callback(device_id, path, size, mtime_ns, quick_hash, classification)` that pipeline calls as it processes each file. For chunked pipeline: when we hash a file (or when we have its metadata from discovery), we call the callback. The callback does `inventory.upsert_file(...)`. Pipeline doesn't need to hold the full list; it streams to inventory as it goes.

**Simpler 7A:** Don't integrate with pipeline yet. Add `InventoryDB` and a **post-scan population** that iterates over `groups` only. For each path in each group, we have path, size, and we can get mtime from stat. We upsert. This populates inventory for duplicate files only. Next phase (7B) can extend to full discovery. **This is the minimal 7A.**

**Refined 7A scope:**

1. Add `InventoryDB` with schema and `upsert_file`, `get_or_create_device`.
2. Add a **populate_from_scan_result** method: given `scan_id`, `scan_root`, `groups`, iterate over all paths in groups, stat each file for mtime, get quick_hash from group data, upsert to inventory. Device from scan_root.
3. Worker calls `inventory.populate_from_scan_result(...)` after `store.write_scan_result(...)`.
4. No pipeline changes. No unchanged/new/changed during scan yet — that's 7B.

**Validation:** First scan → inventory has rows for all files in duplicate groups. Second scan of same root → we could optionally skip re-hashing for files already in inventory with same size/mtime. But that requires pipeline to consult inventory — 7B. For 7A, we just populate. Second scan will overwrite/update. Good enough.

### 4.4 Unchanged file reuse (7A or 7B?)

**7A minimal:** Populate only. No reuse.

**7A extended:** When populating, if file exists in inventory with same size, mtime, quick_hash → mark as `unchanged`, update last_seen. Don't need to re-hash (we already have hash from pipeline). So we're not "skipping work" — pipeline already did the work. We're just recording it correctly. The "reuse" is for **future** scans: in 7B, when we discover a file, we check inventory first. If unchanged, we skip hashing. So 7A = schema + populate. 7B = consult inventory during discovery/hashing.

---

## 5. File-by-File Changes

| File | Change |
|------|--------|
| **New: `cerebro/services/inventory_db.py`** | InventoryDB class; schema; get_or_create_device; upsert_file; populate_from_scan_result |
| `cerebro/workers/fast_scan_worker.py` | After store write, call inventory.populate_from_scan_result if inventory enabled |
| `cerebro/ui/controllers/live_scan_controller.py` | Pass inventory flag from config (optional) |
| Config | Optional `CEREBRO_USE_INVENTORY=1` or settings flag |

---

## 6. populate_from_scan_result Contract

```python
def populate_from_scan_result(
    self,
    scan_id: str,
    scan_root: str,
    groups: List[Dict[str, Any]],
) -> Dict[str, int]:
    """
    Upsert all files in duplicate groups to inventory.
    Returns {added: N, updated: N, unchanged: N}.
    """
```

For each path in each group:
- device_id = get_or_create_device(scan_root)
- path, size from group file; mtime from stat (or from group if we store it)
- quick_hash from group["hash"]
- upsert_file → classification
- Accumulate counts

---

## 7. Validation Checklist

| Test | Expected |
|------|----------|
| First scan of folder with duplicates | inventory_files has rows for each path in groups |
| devices table | One row for scan_root |
| Second scan same folder | Rows updated; last_seen_scan_id, last_seen_timestamp refreshed |
| Scan with no duplicates | inventory empty (we only populate from groups) — acceptable for 7A |

---

## 8. Definition of Done (Phase 7A)

- [ ] `InventoryDB` implemented with devices + inventory_files schema
- [ ] `get_or_create_device` works with path-based device_id
- [ ] `upsert_file` returns classification
- [ ] `populate_from_scan_result` upserts all paths in groups
- [ ] Worker calls populate after store write (when enabled)
- [ ] First scan populates; second scan updates
- [ ] No regression in scan flow

---

## 9. Suggested Commit

```
feat(inventory): add persistent global file inventory

- Add cerebro/services/inventory_db.py with devices + inventory_files schema
- populate_from_scan_result upserts files from duplicate groups
- Worker integrates after store write when CEREBRO_USE_INVENTORY=1
```

---

*Phase 7A implementation spec.*
