# CEREBRO v6.1 — Phase 6B: Pipeline Chunking Foundation

**Branch:** `v6.1-scale-foundation`  
**Phase:** 6B — First code phase for Epic A (Streaming / Chunked Pipeline)  
**Reference:** `V6_1_PIPELINE_STREAMING_PLAN.md`, `V6_1_SCALE_FOUNDATION_PLAN.md`

---

## 1. Objective

Introduce chunked discovery and chunked size aggregation so the pipeline no longer materializes a full `List[FastFileInfo]` in memory. Result-store contract and Review flow remain unchanged.

---

## 2. Scope (Phase 6B Only)

| In scope | Out of scope |
|----------|--------------|
| Chunked discovery API | Incremental group write to store |
| Chunked size aggregation | Candidate reduction (Phase 6C) |
| Same result-store write path | Inventory (Phase 7) |
| Worker progress across chunks | Chunked hashing (future) |
| App remains runnable | UI changes |

---

## 3. Current vs Target

### 3.1 Current flow

```
FastDiscovery.scan() → List[FastFileInfo]  (full list in memory)
         ↓
size_map = Dict[size → List[FastFileInfo]]  (all candidates)
         ↓
candidates = flatten(size_map where count>1)
         ↓
hash_groups = hash(candidates)
         ↓
groups = build from hash_groups
         ↓
return {ok, groups, stats}  → worker writes store
```

### 3.2 Target flow (Phase 6B)

```
FastDiscovery.scan_chunked() → Iterator[List[FastFileInfo]]
         ↓
For each chunk:
  - merge size_counts (Dict[int, int])
  - for duplicate sizes: collect paths → candidates
         ↓
candidates = List[FastFileInfo]  (still in memory for now; hashing unchanged)
         ↓
hash_groups = hash(candidates)  (unchanged)
         ↓
groups = build from hash_groups
         ↓
return {ok, groups, stats}  → worker writes store (unchanged)
```

**Key change:** Discovery and size aggregation are chunked. Candidates list and hashing stay as today. Memory win: we never hold the full file list; we only hold `size_counts` + `candidates` (which is smaller than full list).

---

## 4. Implementation Plan

### 4.1 Add `scan_chunked` to FastDiscovery

**File:** `cerebro/engine/pipeline/fast_pipeline.py`

**New method signature:**

```python
def scan_chunked(
    self,
    root: Path,
    *,
    include_hidden: bool,
    follow_symlinks: bool,
    allowed_exts: Optional[List[str]],
    exclude_dirs: Optional[List[str]],
    min_size: int,
    cancel_check: Callable[[], bool],
    progress_callback: Optional[Callable[[int], None]] = None,
    chunk_size: int = 10_000,
) -> Iterator[List[FastFileInfo]]:
    """
    Yield chunks of FastFileInfo. Never materialize full list.
    Same filtering logic as scan(); yields when len(chunk) >= chunk_size or at end.
    """
```

**Behavior:**

- Same scandir loop as `scan()`.
- Accumulate into `chunk: List[FastFileInfo]`.
- When `len(chunk) >= chunk_size`: `yield chunk`; `chunk = []`.
- At end of scan: `if chunk: yield chunk`.
- `progress_callback(count)` called with cumulative count (sum of all chunks yielded so far).
- `cancel_check()` honored between entries and before each yield.

**Keep `scan()`:** Preserve existing `scan()` for backward compatibility; callers can migrate to `scan_chunked` when ready.

---

### 4.2 Chunked size aggregation in FastPipeline

**File:** `cerebro/engine/pipeline/fast_pipeline.py`

**Replace:**

```python
files = self.discovery.scan(...)
size_map: Dict[int, List[FastFileInfo]] = {}
for f in files:
    size_map.setdefault(f.size, []).append(f)
candidates: List[FastFileInfo] = []
for _, arr in size_map.items():
    if len(arr) > 1:
        candidates.extend(arr)
```

**With:**

```python
size_counts: Dict[int, int] = {}
candidates: List[FastFileInfo] = []

for chunk in self.discovery.scan_chunked(
    ...,
    chunk_size=chunk_size,  # e.g. 10_000
):
    if cancelled():
        break
    # Merge counts
    for f in chunk:
        size_counts[f.size] = size_counts.get(f.size, 0) + 1
    # Collect candidates for duplicate sizes only
    for f in chunk:
        if size_counts[f.size] > 1:
            candidates.append(f)

# Optional: discard size_counts after loop (no longer needed)
```

**Memory:** We hold one chunk at a time + `size_counts` (compact) + `candidates`. `candidates` is smaller than full file list (only duplicate-size files).

---

### 4.3 Progress contract

**Discovery phase:**

- Emit `files_scanned` as cumulative count across chunks.
- Progress callback receives total so far (e.g. 10k, 20k, 30k…).
- Percent: `min(18, int(18 * count / max(1, estimated_total)))` — if total unknown, use count-based progress or fixed discovery cap (e.g. 18% max).

**Option:** First pass for count-only, then second pass for candidates. Simpler progress (we know total after pass 1) but doubles I/O. **Phase 6B recommendation:** Single pass with chunked collection; progress based on cumulative count. For very large scans, discovery % can cap at 18% until we transition to grouping.

---

### 4.4 Parameters

**New optional parameter to `run_fast_scan`:**

```python
chunk_size: int = 10_000,  # Discovery chunk size; 0 = use legacy scan()
```

**ScanEngine / worker:** Pass `chunk_size` through if provided. Default 10_000 for chunked path; 0 to force legacy `scan()`.

---

## 5. File-by-File Changes

| File | Change |
|------|--------|
| `fast_pipeline.py` | Add `FastDiscovery.scan_chunked()`; in `run_fast_scan`, use chunked aggregation when `chunk_size > 0`; add `chunk_size` param |
| `scan_engine.py` | Add `chunk_size` param to `run_scan`; pass through to pipeline |
| `fast_scan_worker.py` | Pass `chunk_size` from config (e.g. `config.get("chunk_size", 10_000)`) when calling pipeline; no change to completion payload |

---

## 6. Result-Store Write Path

**Unchanged.** Worker still receives `{ok, groups, stats}` from pipeline. Worker still calls `store.write_scan_result(scan_id, scan_root, groups, ...)`. No `append_group` or incremental write in Phase 6B.

---

## 7. Validation Checklist

| Test | Expected |
|------|----------|
| Small scan (e.g. 100 files, few duplicates) | Same duplicate group count as baseline (pre-6B) |
| Medium scan (e.g. 10k files) | Same duplicate count; summary correct |
| Large scan (e.g. 100k+ files) | Lower peak memory; same results |
| Review load by scan_id | Works; groups from store |
| Delete flow | Works; propagation correct |
| Progress bar | Stable; no large backward jumps |
| Cancel during discovery | Stops cleanly; no crash |
| `chunk_size=0` | Falls back to legacy `scan()`; same behavior as before |

---

## 8. Backward Compatibility

- `FastDiscovery.scan()` remains; existing callers unchanged.
- `chunk_size=0` or omitted: use `scan()` and current aggregation (no chunking).
- `chunk_size > 0`: use `scan_chunked()` and chunked aggregation.
- Output schema (`groups`, `stats`) identical.

---

## 9. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Chunk boundary splits size group | Not an issue: we merge `size_counts` across chunks; candidates collected when `size_counts[size] > 1`. A size can span chunks. |
| Progress "jumps" | Discovery % based on cumulative count; grouping/hashing phases unchanged. |
| Regression in duplicate count | Validate on known datasets before/after. |
| Performance regression | Chunked path adds loop overhead; expect similar or better (less allocation). Benchmark if needed. |

---

## 10. Definition of Done (Phase 6B)

- [ ] `FastDiscovery.scan_chunked()` implemented and tested
- [ ] `FastPipeline.run_fast_scan()` uses chunked aggregation when `chunk_size > 0`
- [ ] `chunk_size` plumbed through ScanEngine and worker
- [ ] Small scan produces same results as baseline
- [ ] Review and delete flow unchanged
- [ ] App runs without regression

---

## 11. Suggested Commit

```
refactor(pipeline): introduce chunked discovery flow

- Add FastDiscovery.scan_chunked() yielding file chunks
- Use chunked size aggregation in FastPipeline when chunk_size > 0
- Plumb chunk_size through ScanEngine and FastScanWorker
- Preserve scan() for backward compatibility; chunk_size=0 uses legacy path
```

---

*Phase 6B implementation spec. Code changes to follow.*
