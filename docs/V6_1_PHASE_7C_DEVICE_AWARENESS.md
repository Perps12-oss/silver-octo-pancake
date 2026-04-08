# CEREBRO v6.1 — Phase 7C: Device Awareness

**Branch:** `v6.1-scale-foundation`  
**Phase:** 7C — Epic B (Global Inventory + Device-Aware Matching)  
**Reference:** `V6_1_INVENTORY_SCHEMA.md`, `V6_1_PHASE_7B_GLOBAL_MATCHING.md`

---

## 1. Objective

Model removable/internal/network storage. Preserve indexed files from offline devices. Do not treat offline device absence as deletion. Expose device status in Hub and Review truth labels.

---

## 2. Scope (Phase 7C Only)

| In scope | Out of scope |
|----------|--------------|
| Device type: internal/removable/network | UI redesign |
| Offline device detection | New themes |
| is_online in devices table | Broad settings |
| indexed_offline match label | |
| Hub device status | |
| Do not delete when device offline | |

---

## 3. Design Rules

| Rule | Meaning |
|------|---------|
| Offline = device not mounted | Don't treat as "file deleted" |
| Indexed offline matches | Visible in Review; not deletable |
| Reconnect updates state | Device comes back online; refresh |
| Hub shows device status | Online/offline per device |

---

## 4. Device Identity (Full)

### 4.1 Phase 7A vs 7C

**7A:** Path-based device_id (hash of root path). Works but doesn't survive remount with different letter (Windows) or path (Linux).

**7C:** Platform-specific volume identity where available.

| Platform | Approach |
|----------|----------|
| **Windows** | `ctypes` + `GetVolumeInformationByHandleW` → Volume GUID. Fallback: drive letter + label. |
| **macOS** | `stat.st_dev` + mount path; or `diskutil info` for UUID. |
| **Linux** | `/dev/disk/by-uuid/<uuid>` symlink target; or `stat.st_dev`. |
| **Fallback** | `hashlib.sha256(root_path.encode()).hexdigest()[:16]` |

### 4.2 New module: `cerebro/services/device_identity.py`

```python
def get_device_id(root_path: str) -> str:
    """Return stable device ID for root. Uses platform APIs when available."""
    # Windows: Volume GUID
    # macOS: volume UUID or st_dev
    # Linux: UUID from /dev/disk/by-uuid
    # Fallback: path hash
```

```python
def get_device_type(root_path: str) -> str:
    """Return 'internal' | 'removable' | 'network'."""
    # Windows: GetDriveType
    # macOS: IOKit / diskutil
    # Linux: /sys/block, udev, etc.
```

---

## 5. Offline Detection

### 5.1 When is a device offline?

- **Windows:** Path no longer accessible; GetVolumeInformation fails; drive letter gone
- **macOS/Linux:** Mount point not in `/proc/mounts` or equivalent; path stat fails

### 5.2 Detection points

1. **At scan start:** For each device in inventory, check if root_path is accessible. Update is_online.
2. **At Hub load:** Refresh device status for all devices.
3. **Before delete:** If any file in delete plan is on offline device, abort or warn.

### 5.3 Implementation

**InventoryDB:**

```python
def refresh_device_status(self) -> None:
    """Check each device's root_path; set is_online=1 if accessible, 0 otherwise."""
    for row in self._get_all_devices():
        if self._path_accessible(row["root_path"]):
            self._update_device(row["device_id"], is_online=1, last_seen=time.time())
        else:
            self._update_device(row["device_id"], is_online=0)
```

```python
def _path_accessible(self, path: str) -> bool:
    """Return True if path exists and is readable."""
    try:
        return os.path.exists(path) and os.access(path, os.R_OK)
    except Exception:
        return False
```

---

## 6. Review Truth Labels

### 6.1 Match sources (from 7B)

| Label | Meaning | Deletable |
|-------|---------|-----------|
| Current scan | In this scan's roots | Yes |
| Indexed | In inventory, device online | No |
| Indexed offline | In inventory, device offline | No |

### 6.2 Phase 7C addition

- Ensure `indexed_offline` is set when device is offline
- When loading group details, check device status for each indexed path
- Display "Offline" or icon for indexed_offline files

---

## 7. Hub Device Status

### 7.1 Data to show

| Column | Source |
|--------|--------|
| Device | device_label |
| Type | device_type |
| Root | root_path |
| Status | is_online ? "Online" : "Offline" |
| Last seen | last_seen_timestamp |
| Files | COUNT from inventory_files |

### 7.2 Implementation

- Hub page (or new section) queries `InventoryDB.get_devices_with_counts()`
- Call `refresh_device_status()` on load
- Display table or list
- Minimal UI — no redesign

---

## 8. Delete Safety

### 8.1 Rules

- Never include `indexed_offline` in delete plan
- If user somehow selects an indexed file (advanced override), and its device is offline, reject
- Before execute: verify all paths in delete plan are accessible (device online)

### 8.2 Implementation

- Delete engine: filter out any path with match_source=indexed_offline
- Pre-execute check: for each path, ensure file exists and is writable

---

## 9. File-by-File Changes

| File | Change |
|------|--------|
| **New: `cerebro/services/device_identity.py`** | get_device_id, get_device_type (platform-specific) |
| `inventory_db.py` | Use device_identity; add refresh_device_status; get_devices_with_counts |
| `fast_pipeline.py` | Pass device_id from device_identity when creating/updating device |
| Review page | Ensure indexed_offline displayed; no delete for offline |
| Hub page | Add device status section; refresh on load |
| Deletion engine | Filter indexed_offline; pre-execute path check |

---

## 10. Validation Checklist

| Test | Expected |
|------|----------|
| Dataset D: index external drive, disconnect, scan another | Groups show indexed_offline for external paths |
| indexed_offline in Review | Visible; not in delete plan |
| Reconnect drive | refresh_device_status sets is_online=1 |
| Hub | Shows device list with Online/Offline |
| Delete with offline file in plan | Rejected or filtered |

---

## 11. Definition of Done (Phase 7C)

- [ ] device_identity.py with platform-specific get_device_id, get_device_type
- [ ] refresh_device_status updates is_online
- [ ] indexed_offline correctly set when device offline
- [ ] Review shows offline label; excludes from delete
- [ ] Hub shows device status
- [ ] Delete rejects/filters offline paths
- [ ] Reconnect updates state correctly

---

## 12. Suggested Commit

```
feat(devices): add device-aware offline match handling

- Add device_identity.py for volume UUID / device type
- refresh_device_status for offline detection
- indexed_offline in Review; exclude from delete plan
- Hub device status section
```

---

*Phase 7C implementation spec.*
