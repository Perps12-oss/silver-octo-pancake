# CEREBRO v6.1 — Scale Foundation Plan

**Branch:** `v6.1-scale-foundation`  
**Mission:** Build the scale foundation without reopening the now-stable v6 UX.

---

## 1. Scope

This branch is **only** for:

- **Phase 6** — Stream/chunk pipeline
- **Phase 7** — Global inventory + device-aware indexing

**Not** for:

- UI redesign
- New themes
- New scanner toys
- Broad settings changes
- Random polish

---

## 2. Objective

Make CEREBRO capable of handling **500k–1M file libraries** more safely and more intelligently.

---

## 3. Success Criteria

By the end of this branch:

| Criterion | Description |
|-----------|-------------|
| No giant in-memory blobs | Scan no longer depends on full `List[FastFileInfo]` or full `groups` list as primary architecture |
| Reduced memory pressure | Discovery, hashing, grouping reduce peak memory and late-stage stalls |
| Reuse prior knowledge | Repeated scans reuse persisted inventory metadata |
| Cross-root matching | Duplicate matching compares against all indexed files by default |
| Safe removable storage | Removable/offline storage is modeled; offline matches visible but not deletable by default |
| Review remains truthful | Review stays query-backed; no regression in delete/store path |

---

## 4. Epic Overview

### Epic A — Streaming / Chunked Pipeline

**Goal:** Reduce peak memory and late-stage stalls.

**Deliverables:**

- Chunked or streaming discovery
- Earlier candidate reduction
- Reduced full-list materialization
- Stable worker progress across chunks
- No regression in delete/review/store-backed result path

**Key design rules:**

- DB/store is truth
- Memory is working set
- Pipeline reduces problem size continuously
- No giant `List[FastFileInfo]` as primary architecture

### Epic B — Global Inventory + Device-Aware Matching

**Goal:** Make duplicate matching global by default.

**Deliverables:**

- Persistent inventory DB
- Device table / device identity
- Unchanged/new/changed file classification
- Global duplicate scope default
- Delete scope remains current roots only by default
- Offline device awareness in result truth

**Key design rules:**

- Match scope: `ALL_INDEXED_FILES` by default
- Delete scope: `CURRENT_SCAN_ROOTS_ONLY` by default
- Indexed matches must be labeled clearly
- Offline matches visible but not deletable by default

---

## 5. Implementation Phases

| Phase | Description | Output | Doc |
|-------|-------------|--------|-----|
| **6A** | Read-only design pass | Architecture plans | `V6_1_SCALE_FOUNDATION_PLAN.md`, `V6_1_INVENTORY_SCHEMA.md`, `V6_1_PIPELINE_STREAMING_PLAN.md` |
| **6B** | Pipeline chunking foundation | Chunked discovery; size aggregation | `V6_1_PHASE_6B_PIPELINE_CHUNKING.md` |
| **6C** | Candidate reduction hardening | Early elimination of singletons | `V6_1_PHASE_6C_CANDIDATE_REDUCTION.md` |
| **7A** | Inventory schema + persistence | `files` + `devices` tables | `V6_1_PHASE_7A_INVENTORY_PERSISTENCE.md` |
| **7B** | Global matching default | Match vs all indexed; UI labels | `V6_1_PHASE_7B_GLOBAL_MATCHING.md` |
| **7C** | Device awareness | Offline handling; Hub status | `V6_1_PHASE_7C_DEVICE_AWARENESS.md` |

### 5.1 Documentation Index

| Document | Purpose |
|----------|---------|
| `V6_1_SCALE_FOUNDATION_PLAN.md` | This file — branch charter, scope, success criteria |
| `V6_1_INVENTORY_SCHEMA.md` | Inventory + devices schema; file classification; Review labels |
| `V6_1_PIPELINE_STREAMING_PLAN.md` | Streaming/chunking architecture; memory model; pipeline flow |
| `V6_1_PHASE_6B_PIPELINE_CHUNKING.md` | Phase 6B implementation spec — chunked discovery, size aggregation |
| `V6_1_PHASE_6C_CANDIDATE_REDUCTION.md` | Phase 6C implementation spec — early singleton elimination |
| `V6_1_PHASE_7A_INVENTORY_PERSISTENCE.md` | Phase 7A implementation spec — inventory DB, device table, population |
| `V6_1_PHASE_7B_GLOBAL_MATCHING.md` | Phase 7B implementation spec — global scope, match-source labels |
| `V6_1_PHASE_7C_DEVICE_AWARENESS.md` | Phase 7C implementation spec — offline detection, Hub, delete safety |

---

## 6. File Groups per Epic

### Pipeline group (Epic A)

- `cerebro/engine/pipeline/scan_engine.py`
- `cerebro/engine/pipeline/fast_pipeline.py`
- Discovery-related engine files
- Worker completion/progress contracts
- Scan result store write path

### Inventory/device group (Epic B)

- `cerebro/services/inventory_db.py` (new)
- Config/settings for duplicate scope default
- Domain models for scope/device state
- History/audit summary fields if needed

### UI truth extension group (minimal)

- Scan summary wording
- Review labels for indexed/current/offline
- Hub device status
- Optional settings duplicate-scope control

**Do not** do broad UI redesign in this branch.

---

## 7. Rules for This Branch

- No visual redesigns
- No theme overhauls
- No unrelated bug hunts unless they block Phase 6/7
- No new experimental scanner work
- No controller relocation
- No broad settings expansion beyond scope/deletion/inventory needs

This branch should feel **boring and surgical**.

---

## 8. Testing Strategy

### Must-have datasets

| Dataset | Purpose |
|---------|---------|
| **A** | Small local duplicates — same folder, known pairs |
| **B** | Large repeated scan — same root twice; verify unchanged-file reuse |
| **C** | Cross-root duplicates — duplicates across folders/drives; verify global matching |
| **D** | Removable/offline device — indexed external root; disconnect; scan another; verify offline indexed match behavior |

---

## 9. Definition of Done

- [ ] Chunked/streaming architecture exists
- [ ] Result-store contract remains intact
- [ ] Repeated scans benefit from persisted inventory
- [ ] Cross-root duplicates work by default
- [ ] Removable/offline devices handled safely
- [ ] Delete scope remains conservative
- [ ] No regression in review/delete flow

---

## 10. Recommended Commit Sequence

1. `docs(v6.1): add scale foundation architecture plan`
2. `refactor(pipeline): introduce chunked discovery flow`
3. `refactor(pipeline): add early candidate reduction`
4. `feat(inventory): add persistent global file inventory`
5. `feat(scope): enable global indexed matching by default`
6. `feat(devices): add device-aware offline match handling`
7. `test(v6.1): add scale and cross-root validation scenarios`

---

*Phase 6A — Read-only design. No code edits.*
