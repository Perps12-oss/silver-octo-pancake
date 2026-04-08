# CEREBRO v6.1 — Phase 7B: Global Matching Default

**Branch:** `v6.1-scale-foundation`  
**Phase:** 7B — Epic B (Global Inventory + Device-Aware Matching)  
**Reference:** `V6_1_INVENTORY_SCHEMA.md`, `V6_1_PHASE_7A_INVENTORY_PERSISTENCE.md`

---

## 1. Objective

Make duplicate matching **global by default**. Current scan compares against all indexed files. UI summary and Review truth labels show: **current scan**, **indexed match**, **indexed offline**. Delete scope remains current roots only by default.

---

## 2. Scope (Phase 7B Only)

| In scope | Out of scope |
|----------|--------------|
| Match scope: ALL_INDEXED_FILES default | Device offline detection (Phase 7C) |
| Pipeline consults inventory for matching | Broad UI redesign |
| Review labels: current / indexed / indexed_offline | New themes |
| Delete scope: CURRENT_SCAN_ROOTS_ONLY | Settings overhaul |
| match_source in group file metadata | |

---

## 3. Design Rules

| Rule | Meaning |
|------|---------|
| Match scope | Compare current scan files against inventory (all indexed) by default |
| Delete scope | Only files in current scan roots are deletable by default |
| Indexed matches | Labeled clearly; not deletable unless advanced override |
| Offline matches | Visible; not deletable (Phase 7C refines) |

---

## 4. Match Flow

### 4.1 Current (pre-7B)

1. Discover files in scan root(s)
2. Group by size → candidates
3. Hash candidates
4. Build groups (hash → paths, all from current scan)
5. Write to result store

### 4.2 Target (7B)

1. Discover files in scan root(s)
2. For each file: check inventory for same (size, mtime, quick_hash) or same path
   - **Unchanged:** Reuse quick_hash from inventory; skip re-hashing
   - **New:** Hash; add to inventory
   - **Changed:** Re-hash; update inventory
3. Group by size → candidates (current scan files)
4. Hash candidates (with inventory reuse for unchanged)
5. **Match step:** For each hash group, query inventory for other paths with same quick_hash
   - Current scan paths: in this scan's roots
   - Indexed paths: in inventory, same hash, different root, device online
   - Indexed offline: in inventory, same hash, device offline
6. Build groups with `match_source` per path
7. Write to result store (extended schema for match_source)

---

## 5. Schema Extensions

### 5.1 group_files extension

Add `match_source` to each file in a group:

| Value | Meaning |
|-------|---------|
| `current_scan` | File in this scan's roots |
| `indexed` | File in inventory, device online, different root |
| `indexed_offline` | File in inventory, device offline |

**ScanResultStore / group_files:** Add column `match_source TEXT DEFAULT 'current_scan'`.

**Migration:** Existing rows default to `current_scan`.

### 5.2 Scan config

Add to scan options:
- `match_scope`: `current_scan_only` | `all_indexed` (default)
- `delete_scope`: `current_roots_only` | `all_selected` (default: current_roots_only)

---

## 6. Implementation Plan

### 6.1 Pipeline changes

**File:** `fast_pipeline.py`

- After building hash_groups (hash → paths from current scan), for each hash:
  - Query inventory: `SELECT path, device_id FROM inventory_files WHERE quick_hash = ? AND is_present = 1`
  - For each inventory path not in current scan roots:
    - Check device is_online → `indexed` or `indexed_offline`
    - Add to group with match_source
- Pass match_source through to group structure: `{"hash", "paths", "count", "files": [{"path", "match_source"}, ...]}`

### 6.2 Inventory query

**InventoryDB method:**

```python
def get_paths_by_hash(self, quick_hash: str, exclude_device_ids: Optional[Set[str]] = None) -> List[Tuple[str, str, bool]]:
    """
    Returns [(path, device_id, is_online), ...] for all inventory files with this hash.
    exclude_device_ids: current scan's device(s) — don't return those (they're in current scan)
    """
```

### 6.3 Result store extension

**ScanResultStore.write_scan_result:** Accept groups with optional `files` list per group:

```python
# Current: group = {"hash", "paths", "count"}
# New:     group = {"hash", "paths", "count", "files": [{"path": p, "match_source": "current_scan"|"indexed"|"indexed_offline"}, ...]}
```

If `files` present, use it; else derive from paths with match_source=current_scan.

**group_files table:** Add `match_source TEXT DEFAULT 'current_scan'`.

### 6.4 Review page

- When loading group details, include match_source per file
- File table: show badge/icon for indexed, indexed_offline
- Delete plan: only include paths with match_source=current_scan (unless delete_scope=all_selected and user confirmed)

### 6.5 Scan summary

- Add line: "X groups (Y current, Z indexed)" or similar
- Optional: "Z indexed (W offline)"

---

## 7. File-by-File Changes

| File | Change |
|------|--------|
| `inventory_db.py` | Add `get_paths_by_hash(quick_hash, exclude_device_ids)` |
| `fast_pipeline.py` | After hash groups, query inventory; merge indexed paths with match_source |
| `scan_result_store.py` | Add match_source to group_files; handle files with match_source in write |
| `review_page.py` | Display match_source per file; filter delete plan by match_source |
| Config/bus | Add match_scope, delete_scope to scan options |

---

## 8. Safety

| Concern | Mitigation |
|--------|------------|
| Deleting indexed file by mistake | Delete plan excludes indexed/offline by default |
| Offline file shown as deletable | match_source=indexed_offline → never in default delete plan |
| Performance: inventory query per hash | Batch query: get all hashes, single query with IN clause |
| Empty inventory | Fall back to current-scan-only; same as pre-7B |

---

## 9. Validation Checklist

| Test | Expected |
|------|----------|
| Dataset C: cross-root duplicates | Both roots scanned; groups show paths from both; match_source correct |
| Delete: only current-scan files | Indexed paths not in delete plan |
| current_scan_only mode | Same as pre-7B; no inventory lookup |
| Review labels | Badge/icon per file for current vs indexed vs offline |

---

## 10. Definition of Done (Phase 7B)

- [ ] match_scope=all_indexed by default
- [ ] Pipeline queries inventory for each hash; merges indexed paths
- [ ] match_source stored in group_files
- [ ] Review shows match_source per file
- [ ] Delete scope excludes indexed/offline by default
- [ ] current_scan_only mode works (no regression)
- [ ] Cross-root duplicate detection works

---

## 11. Suggested Commit

```
feat(scope): enable global indexed matching by default

- Pipeline queries inventory for cross-root matches
- Add match_source to group_files (current_scan|indexed|indexed_offline)
- Review displays match source; delete plan excludes indexed by default
- match_scope and delete_scope config options
```

---

*Phase 7B implementation spec.*
