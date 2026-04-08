# CEREBRO v6.1 — Pipeline Streaming Plan

**Phase 6A — Read-only design.** No code edits.

---

## 1. Current Architecture (Summary)

Today's `FastPipeline` and `FastDiscovery`:

| Step | Component | Memory usage |
|------|-----------|--------------|
| 1 | `FastDiscovery.scan()` | Returns **full** `List[FastFileInfo]` — all files in memory |
| 2 | Size grouping | `size_map: Dict[int, List[FastFileInfo]]` — all candidates in memory |
| 3 | `candidates` | `List[FastFileInfo]` — duplicate-size files only, still full list |
| 4 | Hashing | `hash_groups: Dict[str, List[str]]` — paths per hash; `to_hash` list |
| 5 | Finalization | `groups = [{hash, paths, count}, ...]` — full result in memory |

**Problem:** For 500k files, we hold ~500k `FastFileInfo` objects, then `size_map`, then `candidates`, then `hash_groups`. Peak memory scales with file count.

---

## 2. Design Rules

| Rule | Meaning |
|------|---------|
| DB/store is truth | Result-store holds groups; memory is transient |
| Memory is working set | Only current chunk + reduced candidates |
| Pipeline reduces continuously | Each stage shrinks the problem |
| No giant `List[FastFileInfo]` | Discovery yields chunks; never materialize full list |

---

## 3. What Remains in Memory

| Data | Size | Lifecycle |
|------|------|-----------|
| Current discovery chunk | ~N files (e.g. 5k–20k) | Processed, then discarded |
| Per-chunk size→paths | Only for current chunk | Flush to next stage |
| Accumulated size→counts | `Dict[int, int]` — size → count | Compact; no full path lists |
| Candidate paths (for hashing) | Only files in duplicate sizes | Streamed to hasher |
| Hash groups (in progress) | Growing until done | Written incrementally to store |
| Worker progress state | Minimal | Percent, message, stats |

---

## 4. What Moves to Persistent Store

| Data | Store | When |
|------|-------|------|
| Duplicate groups | ScanResultStore | As groups complete (incremental write) or at end |
| File inventory | InventoryDB (Phase 7) | Per-file as classified |
| Hash cache | HashCache (existing) | Per-file on hash compute |

---

## 5. How Chunking Works

### 5.1 Discovery yields chunks

**Current:** `FastDiscovery.scan()` returns `List[FastFileInfo]`.

**New:** `FastDiscovery.scan_chunked()` is a generator or callback-based:

```python
def scan_chunked(self, ..., chunk_size: int = 10_000) -> Iterator[List[FastFileInfo]]:
    """Yield chunks of FastFileInfo. Never hold full list."""
    chunk: List[FastFileInfo] = []
    # ... same scandir loop ...
    # When len(chunk) >= chunk_size: yield chunk; chunk = []
    # At end: if chunk: yield chunk
```

Alternative: callback `on_chunk(List[FastFileInfo])` — pipeline passes a handler.

### 5.2 Size aggregation without full list

**Current:** `size_map: Dict[int, List[FastFileInfo]]` holds all candidates.

**New:** Two-phase:

1. **Phase 1 — Count only:** `size_counts: Dict[int, int]`. For each chunk, increment `size_counts[size]` for each file. No path storage. Discard chunk after counting.
2. **Phase 2 — Collect candidates:** Second pass (or same pass with delayed yield): for sizes where `count > 1`, collect paths. Can be chunked: only emit paths for duplicate sizes.

**Optimization:** Single-pass with a hybrid structure:
- `size_to_paths: Dict[int, List[str]]` but only for sizes with `count > 1`
- First chunk: build `size_counts`
- Subsequent chunks: add to `size_to_paths` only when `size_counts[size] > 1`
- When a size reaches count 2, create list and backfill from... we need to either store first occurrence or do two passes.

**Simpler approach:** Two-pass discovery.
- Pass 1: `scan_chunked` → for each chunk, update `size_counts` only; discard chunk.
- Pass 2: `scan_chunked` → for each chunk, for each file with `size_counts[size] > 1`, add to `candidates` (or stream to hasher).

Downside: Two full directory walks. For 500k files, that's significant I/O.

**Alternative — single pass with bounded memory:**
- Hold `size_counts: Dict[int, int]`
- Hold `size_to_first_path: Dict[int, str]` — only one path per size (to detect duplicates)
- When we see a second file with same size: we now know it's a candidate. We need both paths. So we must either:
  - Store up to 2 paths per size (then stream to hasher), or
  - Store all paths for duplicate sizes (memory grows again for many duplicates)

**Practical compromise:**
- Chunk discovery.
- Per chunk: compute `size_counts` for chunk; merge into global `size_counts`.
- Per chunk: for each file where `size_counts[size] > 1`, append to `candidates` list.
- `candidates` can still grow large (e.g. 100k files all same size). So we stream candidates to hashing in sub-chunks.

### 5.3 Candidate reduction (Phase 6C)

- **Unique sizes:** Never enter `candidates` (already achieved by size grouping).
- **Singleton partial hashes:** After quick-hash, if only one file has hash H, drop it.
- **Early elimination:** Before full hashing, use size+partial-read signature to drop singletons.

---

## 6. How Groups Are Written Incrementally

**Current:** Build `groups = [{hash, paths, count}, ...]` in memory; return; worker writes to store in one shot.

**New:**

1. **Option A — Batch at end:** Same as today; pipeline produces groups, worker writes. Memory still holds all groups until write. No change to write path.
2. **Option B — Incremental write:** As each hash group completes (2+ files with same hash), immediately write that group to store. Pipeline yields group to writer; writer appends to `duplicate_groups` + `group_files`. Memory holds only in-progress groups.

**Recommendation:** Start with Option A (minimal change). Move to Option B when we have chunked hashing and want to avoid holding all groups.

**Incremental write contract:**
- `ScanResultStore.append_group(scan_id, group_index, group_dict)` — append one group.
- Worker or pipeline calls this as each group completes.
- Final `write_scan_metadata(scan_id, ...)` updates `scans` row with counts.

---

## 7. Pipeline Flow (Proposed)

```
Discovery (chunked)
    │
    ▼
For each chunk:
    ├─► Update size_counts (merge)
    └─► For duplicate sizes: add to candidate_stream
              │
              ▼
    Candidate reduction (Phase 6C)
    - Unique sizes: never added
    - Singleton hashes: drop as discovered
              │
              ▼
    Hashing (chunked consumption)
    - Read from candidate_stream in batches
    - HashCache lookup
    - ThreadPoolExecutor.map in chunks
    - Emit hash groups
              │
              ▼
    Group writer
    - For each complete group: store.append_group(...)
    - Or collect and write at end (Phase 6B)
              │
              ▼
    Progress
    - Stable progress across chunks
    - files_discovered, candidates_remaining, groups_found
```

---

## 8. Worker Progress Contracts

**Current:** `progress_cb(percent, message, stats)` with `phase`, `files_scanned`, `current_path`, etc.

**New:** Same signature. Add:

| Key | Meaning |
|-----|---------|
| `chunk_index` | Current discovery chunk (optional) |
| `candidates_remaining` | Count of files still to hash |
| `groups_written` | Groups written to store so far |

Progress must remain monotonic and meaningful across chunks. Avoid "jumping back" when moving from discovery to hashing.

---

## 9. Result-Store Contract (Unchanged)

ScanResultStore schema and `write_scan_result` contract remain. Pipeline/worker still produce:

```python
groups = [{"hash": h, "paths": [...], "count": n}, ...]
```

Store write path unchanged. Only the *production* of `groups` changes (chunked, lower memory).

---

## 10. Validation (Phase 6B)

| Test | Expected |
|------|----------|
| Small scan (100 files) | Same duplicate count as baseline; summary correct |
| Review load by scan_id | Works; groups from store |
| Delete | Works; propagation correct |
| Progress | Stable; no large backward jumps |

---

## 11. Files to Touch (Phase 6B)

| File | Change |
|------|--------|
| `fast_pipeline.py` | `FastDiscovery.scan_chunked` or callback; chunked size aggregation; optional incremental group write |
| `fast_discovery` (in fast_pipeline) | Generator or callback API |
| `scan_engine.py` | Pass through; may accept chunk_size param |
| `fast_scan_worker.py` | Progress stats for chunks; no change to completion payload |
| `scan_result_store.py` | Optional `append_group` for incremental write; else unchanged |

---

*Phase 6A — Read-only design. No code modified.*
