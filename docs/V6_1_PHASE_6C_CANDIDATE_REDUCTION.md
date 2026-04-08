# CEREBRO v6.1 — Phase 6C: Candidate Reduction Hardening

**Branch:** `v6.1-scale-foundation`  
**Phase:** 6C — Epic A (Streaming / Chunked Pipeline)  
**Reference:** `V6_1_PIPELINE_STREAMING_PLAN.md`, `V6_1_PHASE_6B_PIPELINE_CHUNKING.md`

---

## 1. Objective

Eliminate unique sizes early, eliminate singleton partial hashes early, and avoid carrying dead candidates deep in the pipeline. Reduces memory pressure and CPU work on large scans.

---

## 2. Scope (Phase 6C Only)

| In scope | Out of scope |
|----------|--------------|
| Unique size elimination | Inventory integration (Phase 7) |
| Singleton quick-hash elimination | Chunked hashing (future) |
| Early candidate pruning | UI changes |
| Same duplicate counts as baseline | New hash algorithms |

---

## 3. Current Flow (Post-6B)

```
Discovery (chunked) → size_counts merge + candidates collect
         ↓
candidates = all files with size where count > 1
         ↓
HashCache lookup + hash(to_hash)
         ↓
hash_groups: Dict[hash → List[path]]
         ↓
groups = filter len(paths) >= 2
```

**Problem:** After hashing, we may have hash groups with only one file (e.g. two files same size, different content → different hashes). We currently filter these at finalization. But we also carry them through the entire hashing phase. For large candidate sets with many unique sizes that happen to collide (e.g. many 1MB files), we hash many files that will never form a duplicate group.

---

## 4. Reduction Strategies

### 4.1 Unique sizes (already done in 6B)

Files with unique sizes never enter `candidates`. No change needed.

### 4.2 Singleton quick-hash elimination

**Idea:** After computing quick_hash for a file, if that hash appears only once (so far), we can drop it from the candidate pool for grouping. We only need to keep hashes that have 2+ files.

**Challenge:** We hash in parallel (ThreadPoolExecutor.map). We don't know if a hash is a singleton until we've seen all files with that hash. Options:

- **Option A — Post-hash filter:** After hashing, drop singleton hashes before building groups. Already done (we filter `len(paths) < 2`). No memory win during hashing.
- **Option B — Two-phase hash:** First pass: hash all, build `hash → count`. Second pass: only keep paths for hashes with count > 1. Doubles hash work.
- **Option C — Incremental emit:** As we hash, maintain `hash_groups`. When a hash gets its second file, we "commit" it. Singletons stay in a temp structure; at end we drop them. Memory: we still hold all paths until we know. No win.
- **Option D — Size + partial signature pre-filter:** Before full quick-hash, use size + first N bytes (or mtime) as a cheap signature. If only one file has that signature, skip hashing. Reduces hashing work but adds a pre-pass.

**Recommendation for 6C:** Focus on **reducing the candidate set before hashing** using cheap signals. The main win is **size** (done). Next: **size + mtime** — if two files have same size but different mtime, they're different. But we need same size AND same mtime to be candidates... Actually no: same size is sufficient for candidacy. Different content → different hash → we filter at end. So we can't eliminate before hashing without risking false negatives.

**Practical 6C scope:** Optimize the **order** and **batching** of hashing to fail fast on singletons. When we get a hash result, immediately check: does this hash already have 1 file? If yes, we'll have 2 when we add. If no, we have 1 — but we can't drop until we've seen all. So the only optimization is: **don't store paths for singleton hashes until we see a second**. Use `hash → List[path]` but with a special case: when we add the first path, we could use a "pending" structure. When we add the second, promote to real. When we're done, drop all pending. This saves memory for the (common) case where many sizes have 2 files but hashes split them — we'd have many singleton hashes. By not storing paths for singletons, we only hold the path until we see a duplicate. But we need the path to add the second... So we must hold it. The win is: for singletons, we hold 1 path per hash. For duplicates, we hold N paths. The memory win is in not holding the hash key for "dropped" singletons — we can avoid adding to hash_groups until we have 2. So: **lazy hash_groups**: only add to hash_groups when we get a second file with same hash. First file: store in `pending_singletons: Dict[hash, path]`. Second file with same hash: move both to hash_groups, remove from pending. End: drop pending_singletons.

**Refined 6C deliverable:** Lazy hash group construction — don't add to `hash_groups` until we have 2+ files with same hash. Use a temporary structure for "one file so far" and only promote when we see a duplicate. At end, discard temp. Reduces `hash_groups` size (fewer keys, fewer lists).

### 4.3 Early size-bucket pruning

**Idea:** If a size has only 2 files, we must hash both. If a size has 10,000 files, we'll likely get many hash groups. No way to prune before hashing. But we can **avoid materializing** the full candidate list for huge size buckets by processing them in sub-batches. When a size has 100k files, we could hash in chunks of 5k and emit groups as we go. That's chunked hashing — out of scope for 6C.

**6C scope:** Lazy hash_groups + ensure we're not doing redundant work. Also: **skip HashCache lookup for sizes with only 2 files**? No — we still need the hash for both. Cache helps on re-scan.

---

## 5. Implementation Plan

### 5.1 Lazy hash group construction

**File:** `cerebro/engine/pipeline/fast_pipeline.py`

**Current:**

```python
hash_groups: Dict[str, List[str]] = {}
for f, qh in ex.map(...):
    if qh:
        hash_groups.setdefault(qh, []).append(f.path)
# ...
for h, paths in hash_groups.items():
    if len(paths) < 2:
        continue
    groups.append(...)
```

**New:**

```python
hash_groups: Dict[str, List[str]] = {}   # Only groups with 2+ paths
pending: Dict[str, str] = {}              # hash → single path (candidate for promotion)

def add_hash_result(h: str, path: str) -> None:
    if h in hash_groups:
        hash_groups[h].append(path)
    elif h in pending:
        # Second file with this hash — promote to group
        first = pending.pop(h)
        hash_groups[h] = [first, path]
    else:
        pending[h] = path

# In the map loop:
for f, qh in ex.map(...):
    if qh:
        add_hash_result(qh, f.path)

# End: discard pending (singletons)
# groups = build from hash_groups only
```

**Memory:** `pending` holds at most one path per unique hash that turned out to be a singleton. For 100k candidates with 80k singleton hashes, we hold 80k paths in pending until end. So we don't save memory during the run; we save at the end by not having 80k entries in hash_groups. The real win: hash_groups stays smaller (only duplicate hashes), so final group build is faster. And we avoid the post-loop filter over hash_groups for singletons — they never enter.

**Refinement:** For very large pending, we could periodically try to reclaim. But the main benefit is simpler finalization and slightly smaller hash_groups.

### 5.2 Batch hash cache lookup

**Current:** We iterate over candidates, do cache.get for each, split into cache_hits and to_hash. Fine.

**Optional:** Process cache lookup in batches to improve locality. Low priority for 6C.

---

## 6. File-by-File Changes

| File | Change |
|------|--------|
| `fast_pipeline.py` | Replace `hash_groups.setdefault` with `add_hash_result` (lazy promotion from pending); drop pending at end |
| `scan_engine.py` | No change |
| `fast_scan_worker.py` | No change |

---

## 7. Validation

| Test | Expected |
|------|----------|
| Dataset A (small, known pairs) | Same duplicate count as 6B baseline |
| Dataset with many same-size different-content files | Same duplicate count; lower hash_groups entries during run |
| Large scan (100k+ candidates) | No regression; possibly lower peak memory |

---

## 8. Definition of Done (Phase 6C)

- [ ] Lazy hash group construction implemented
- [ ] Pending singletons discarded at end
- [ ] Same duplicate counts as 6B on test datasets
- [ ] No regression in Review/delete flow

---

## 9. Suggested Commit

```
refactor(pipeline): add early candidate reduction

- Lazy hash group construction: only add to hash_groups when 2+ files share hash
- Pending singletons discarded at end; no singleton entries in hash_groups
- Same duplicate counts; reduced hash_groups size during run
```

---

*Phase 6C implementation spec.*
