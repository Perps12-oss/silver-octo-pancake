# CEREBRO v6.1 — Inventory Schema Design

**Phase 6A — Read-only design.** No code edits.

---

## 1. Purpose

The inventory DB stores **all indexed files** across scans and devices. It enables:

- **Global duplicate matching** — compare current scan against all indexed files
- **Unchanged/new/changed classification** — skip redundant work for unchanged files
- **Device awareness** — model removable/internal/network; handle offline safely
- **Cross-root matching** — find duplicates across different folders/drives

---

## 2. Design Rules

| Rule | Meaning |
|------|---------|
| Match scope | `ALL_INDEXED_FILES` by default |
| Delete scope | `CURRENT_SCAN_ROOTS_ONLY` by default |
| Indexed matches | Must be labeled clearly in Review |
| Offline matches | Visible but not deletable by default |

---

## 3. Schema

### 3.1 Devices table

Stores device identity and status. One row per known storage root (drive letter, mount point, network path).

```sql
CREATE TABLE devices (
    device_id TEXT PRIMARY KEY,           -- stable ID (e.g. volume UUID, path hash)
    device_label TEXT NOT NULL,           -- human label (e.g. "External SSD (E:)")
    device_type TEXT NOT NULL,            -- 'internal' | 'removable' | 'network'
    root_path TEXT NOT NULL UNIQUE,       -- canonical root path
    last_seen_timestamp REAL,             -- last time this device was seen
    is_online INTEGER NOT NULL DEFAULT 1, -- 1 = present, 0 = offline/unmounted
    created_at REAL NOT NULL,
    updated_at REAL
);

CREATE INDEX idx_devices_online ON devices(is_online);
CREATE INDEX idx_devices_root ON devices(root_path);
```

**Device identity:** Use volume UUID where available (Windows: `GetVolumeInformation`; macOS/Linux: mount info). Fallback: stable hash of `root_path` for first-time indexing.

### 3.2 Files inventory table

One row per indexed file. Tracks metadata for duplicate matching and change detection.

```sql
CREATE TABLE inventory_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    path TEXT NOT NULL,                   -- absolute path
    relative_path TEXT,                   -- path relative to device root (optional)
    size_bytes INTEGER NOT NULL,
    mtime_ns INTEGER NOT NULL,
    quick_hash TEXT,                      -- sampled hash (MD5 hex)
    full_hash TEXT,                       -- full-content hash (optional)
    last_seen_scan_id TEXT,               -- last scan that saw this file
    last_seen_timestamp REAL NOT NULL,
    is_present INTEGER NOT NULL DEFAULT 1,-- 1 = file exists, 0 = missing (device offline or deleted)
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
    UNIQUE(device_id, path)
);

CREATE INDEX idx_inventory_device ON inventory_files(device_id);
CREATE INDEX idx_inventory_size ON inventory_files(size_bytes);
CREATE INDEX idx_inventory_quick_hash ON inventory_files(quick_hash);
CREATE INDEX idx_inventory_last_seen ON inventory_files(last_seen_scan_id);
CREATE INDEX idx_inventory_device_present ON inventory_files(device_id, is_present);
```

### 3.3 Scan–inventory linkage (optional)

Links scans to inventory for "what did this scan contribute?"

```sql
CREATE TABLE scan_inventory_links (
    scan_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    files_added INTEGER NOT NULL DEFAULT 0,
    files_updated INTEGER NOT NULL DEFAULT 0,
    files_unchanged INTEGER NOT NULL DEFAULT 0,
    files_removed INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (scan_id, device_id),
    FOREIGN KEY (scan_id) REFERENCES scans(scan_id),
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
);
```

*(Note: `scans` table lives in `scan_result_store`; this links to it.)*

---

## 4. File Classification

When a scan discovers a file, compare against inventory:

| Classification | Condition | Action |
|----------------|-----------|--------|
| **Unchanged** | Same `device_id`, `path`, `size`, `mtime_ns`, `quick_hash` in inventory | Reuse `quick_hash`; skip re-hashing; update `last_seen_scan_id`, `last_seen_timestamp` |
| **Changed** | Same `device_id`, `path` but `size` or `mtime_ns` differs | Re-hash; update inventory row |
| **New** | No row for `device_id` + `path` | Hash; insert new row |
| **Removed** | File was in inventory, not seen this scan, device online | Mark `is_present = 0` or remove (policy TBD) |

---

## 5. Device Identity

### How to obtain `device_id`

| Platform | Approach |
|----------|----------|
| **Windows** | `ctypes` + `GetVolumeInformationByHandleW` → Volume GUID; or hash of `\\?\Volume{...}` |
| **macOS** | `stat.st_dev` + mount path; or `diskutil info` |
| **Linux** | `stat.st_dev` or UUID from `/dev/disk/by-uuid/` |

Fallback: `hashlib.sha256(root_path.encode()).hexdigest()[:16]` for first-time indexing.

### Device types

- **internal** — System drive, fixed internal storage
- **removable** — USB, SD, external drives
- **network** — SMB, NFS, mapped drives

---

## 6. How Review Labels Matches

Review must distinguish match sources for truth and delete safety:

| Label | Meaning | Deletable by default? |
|-------|---------|------------------------|
| **Current scan** | File in this scan's roots | Yes |
| **Indexed** | File in inventory, device online | No (different root) |
| **Indexed offline** | File in inventory, device offline | No |

**UI extension (minimal):**

- Add `match_source` to group file metadata: `current_scan` | `indexed` | `indexed_offline`
- Review file table: show badge or icon per file
- Delete footer: only current-scan files in delete plan unless explicit advanced override

---

## 7. What Remains in Memory vs Persistent Store

| Data | Location | Rationale |
|------|----------|-----------|
| Current chunk of discovered files | Memory | Working set; streamed to grouping |
| Size→candidates map (per chunk) | Memory | Reduced; flushed after grouping |
| Hash groups (incremental) | Memory + Store | Write groups to result-store as completed; memory holds only active window |
| Full file inventory | Store | Too large for memory at scale |
| Device list | Store | Small; can cache in memory |
| Scan result (groups) | Store | Already in `scan_result_store` |

---

## 8. Integration with Existing Stores

| Store | Relationship |
|-------|--------------|
| **ScanResultStore** | Holds scan metadata + duplicate groups. Inventory is separate; scan may *reference* inventory for match-source labels. |
| **HashCache** | Per-file hash cache. Inventory can *use* hash cache for quick_hash; inventory adds persistence of "what we've seen" across scans. |
| **HistoryStore** | Deletion audit. No change; still records deletions by scan_id. |

---

## 9. Migration Path

1. **Phase 7A:** Add `inventory_db.py` with schema; no pipeline integration yet.
2. **Phase 7A:** On scan completion, optionally populate inventory for scanned roots (device_id from root).
3. **Phase 7B:** Pipeline consults inventory for unchanged/new/changed; match against all indexed.
4. **Phase 7C:** Device table; offline detection; Review labels.

---

*Phase 6A — Read-only design. No code modified.*
