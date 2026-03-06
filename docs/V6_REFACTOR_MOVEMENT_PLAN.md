# CEREBRO v6 Refactor Movement Plan (Revised)

**Branch:** `refactor/v6-architecture`  
**Rule:** Commit after each batch as `stageX: <short desc>`.  
**Scope:** Plan only — no code changes in this document.

---

## 1) Proposed Folder Structure (v6)

```
cerebro/
├── app/
│   ├── __init__.py
│   ├── application.py      # NEW: thin wrapper around bootstrap + main window
│   └── bootstrap.py        # NEW: env, logging, config load, crash handler
│
├── domain/
│   ├── __init__.py
│   ├── models.py           # Consolidated scan/deletion/UI-shared models
│   ├── scan_models.py      # Optional split: scan-specific (StartScanConfig, ScanProgress, etc.)
│   └── deletion_models.py  # Optional split: ExecutableDeletePlan, DeletionResult, etc.
│
├── engine/
│   ├── __init__.py
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── pipeline_contract.py   # NEW: ScanEngine protocol / abstract interface
│   │   ├── fast_pipeline.py       # MOVED from core/
│   │   └── cerebro_pipeline.py    # MOVED from core/pipeline.py (delete orchestration only)
│   ├── discovery/
│   │   ├── __init__.py
│   │   ├── discovery.py           # MOVED from core/
│   │   └── discovery_parallel.py  # MOVED from core/discovery_optimized.py
│   ├── hashing/
│   │   ├── __init__.py
│   │   ├── hashing.py             # MOVED from core/
│   │   └── hashing_optimized.py    # MOVED from core/
│   ├── grouping/
│   │   ├── __init__.py
│   │   └── clustering.py          # MOVED from core/ (grouping + clustering)
│   ├── decision/
│   │   ├── __init__.py
│   │   └── decision_engine.py     # MOVED from core/decision.py
│   ├── deletion/
│   │   ├── __init__.py
│   │   └── deletion_engine.py     # MOVED from core/deletion.py
│   └── reporting/                 # CORE: audit/trust — keep if already solid
│       ├── __init__.py
│       ├── json_report.py         # MOVED from core/reporting/
│       └── script_report.py
│
├── scanners/
│   ├── __init__.py         # Scanner registry + re-exports
│   ├── base_scanner.py     # NEW (optional): abstract base
│   ├── simple_scanner.py   # MOVED from core/scanners/
│   ├── advanced_scanner.py
│   ├── turbo_scanner.py
│   ├── ultra_scanner.py    # Extension or experimental per classification
│   └── quantum_scanner.py  # Experimental (heavy deps)
│
├── controllers/
│   ├── __init__.py
│   ├── live_scan_controller.py   # MOVED from ui/controllers/
│   └── review_controller.py      # NEW (optional): extract from review_page logic
│
├── ui/
│   ├── __init__.py
│   ├── main_window.py
│   ├── state_bus.py
│   ├── theme_engine.py
│   ├── pages/
│   │   ├── start_page.py
│   │   ├── scan_page.py
│   │   ├── review_page.py
│   │   ├── history_page.py
│   │   ├── theme_page.py
│   │   ├── settings_page.py
│   │   ├── audit_page.py
│   │   ├── hub_page.py
│   │   ├── base_station.py
│   │   ├── station_navigator.py
│   │   └── delete_confirm_dialog.py
│   ├── widgets/
│   ├── components/
│   └── models/
│       └── live_scan_snapshot.py
│
├── workers/
│   ├── __init__.py
│   ├── base_worker.py
│   ├── scan_worker.py
│   ├── fast_scan_worker.py
│   ├── cleanup_worker.py
│   └── delete_worker.py
│
├── services/                      # Infra only: DB, config, logging
│   ├── __init__.py
│   ├── config.py
│   ├── logger.py
│   ├── performance_monitor.py
│   ├── cache_manager.py
│   ├── hash_cache.py
│   ├── inventory_db.py
│   ├── startup_assertions.py
│   └── update_checker.py
│
├── history/                       # FIRST-CLASS: product capability (audit, resume, accountability)
│   ├── __init__.py
│   ├── store.py                  # KEEP — do not move under services
│   └── models.py                 # KEEP — do not move under services
│
├── utils/                         # STRICT: pure helpers only
│   ├── __init__.py
│   ├── file_utils.py
│   ├── ui_utils.py              # Must not import Qt at module level; or move to ui/utils/
│   ├── validation_utils.py
│   └── startup.py
│
├── extensions/                    # Planned features to ship, not necessarily default
│   ├── __init__.py
│   ├── visual_similarity/
│   │   ├── __init__.py
│   │   └── visual_similarity.py
│   ├── visual_hashing/
│   │   ├── __init__.py
│   │   └── visual_hashing.py
│   ├── gpu_scanners/             # Optional ultra/quantum if classified experimental
│   │   ├── __init__.py
│   │   ├── ultra_scanner.py
│   │   └── quantum_scanner.py
│   └── resume_scan/              # InventoryDB wiring when implemented
│       └── __init__.py
│
└── experimental/                  # Research / heavy deps / uncertain
    ├── __init__.py
    ├── session.py
    ├── scoring.py                # Broken MediaItem / prototype
    ├── curation/
    │   └── scoring.py
    └── eye_opengl/                # OpenGL eye variants, etc.
```

---

### 1.1) Utils — Strict Definition

**Recommendation:** Keep `cerebro/utils/` at root **only if** it is strictly defined as:

- **Pure helpers:** no Qt/PySide6 imports, no I/O at import time, no service side effects.
- Any module that imports UI or performs I/O at import time belongs in its owning layer:
  - Engine helpers → `cerebro/engine/_utils/`
  - UI helpers → `cerebro/ui/utils/`
  - Service helpers → `cerebro/services/utils/`

**Rule:** “Misc utils” becomes a dependency swamp; enforce “no Qt, no I/O at import time” for anything under `cerebro/utils/`. If in doubt, move the module into the layer that owns its dependencies.

---

### 1.2) History — Do Not Move Under Services

**Recommendation:** Do **not** move History to `services/history/`.

- History is a **product capability** (auditability, resuming, accountability), not generic infra.
- **Clean split:** `cerebro/history/` stays a first-class top-level package. `cerebro/services/` contains infra only (DB, config, logging).
- If a move is ever done, keep the name `cerebro/history/` and the package at top level; do not place it under `services/`.
- **Batch 3 (history under services) is postponed/skipped** unless proven low risk and wiring is minimal.

---

### 1.3) Extensions vs Experimental — Classification Rule

| Tier | Meaning | Examples |
|------|--------|----------|
| **extensions/** | Planned features you will ship but not necessarily enabled by default | visual_similarity, visual_hashing, reporting (if not kept core), resume_scan (InventoryDB wiring) |
| **experimental/** | Research / heavy deps / uncertain | quantum_scanner, GPU/ML stacks, OpenGL eye variants, prototype scoring |

- **Reporting:** Audit exports are a **core trust feature**. If reporting is already solid, keep it **core** (e.g. `engine/reporting/`). Do not put it in extensions unless it is optional or not yet part of the main audit flow.
- **Resume (InventoryDB):** Planned extension; when wired, lives under `extensions/resume_scan/` or similar.

---

## 2) File-by-File Move Table

### A) Moves (old_path → new_path)

| Old path | New path | Tier |
|----------|----------|------|
| `cerebro/core/models.py` | `cerebro/domain/models.py` | Core |
| `cerebro/core/fast_pipeline.py` | `cerebro/engine/pipeline/fast_pipeline.py` | Core |
| `cerebro/core/pipeline.py` | `cerebro/engine/pipeline/cerebro_pipeline.py` | Core |
| `cerebro/core/discovery.py` | `cerebro/engine/discovery/discovery.py` | Core |
| `cerebro/core/discovery_optimized.py` | `cerebro/engine/discovery/discovery_parallel.py` | Core |
| `cerebro/core/hashing.py` | `cerebro/engine/hashing/hashing.py` | Core |
| `cerebro/core/hashing_optimized.py` | `cerebro/engine/hashing/hashing_optimized.py` | Core |
| `cerebro/core/grouping.py` | `cerebro/engine/grouping/grouping.py` | Core |
| `cerebro/core/clustering.py` | `cerebro/engine/grouping/clustering.py` | Core |
| `cerebro/core/decision.py` | `cerebro/engine/decision/decision_engine.py` | Core |
| `cerebro/core/deletion.py` | `cerebro/engine/deletion/deletion_engine.py` | Core |
| `cerebro/core/reporting/json_report.py` | `cerebro/engine/reporting/json_report.py` | Core (trust) |
| `cerebro/core/reporting/script_report.py` | `cerebro/engine/reporting/script_report.py` | Core (trust) |
| `cerebro/core/scanners/simple_scanner.py` | `cerebro/scanners/simple_scanner.py` | Core |
| `cerebro/core/scanners/advanced_scanner.py` | `cerebro/scanners/advanced_scanner.py` | Core |
| `cerebro/core/scanners/turbo_scanner.py` | `cerebro/scanners/turbo_scanner.py` | Core |
| `cerebro/core/scanners/ultra_scanner.py` | `cerebro/extensions/gpu_scanners/ultra_scanner.py` | Extension |
| `cerebro/core/scanners/quantum_scanner.py` | `cerebro/experimental/quantum_scanner.py` (or extensions) | Experimental |
| `cerebro/core/scanner_adapter.py` | `cerebro/engine/pipeline/scanner_adapter.py` | Core |
| `cerebro/core/visual_hashing.py` | `cerebro/extensions/visual_hashing/visual_hashing.py` | Extension |
| `cerebro/core/visual_similarity.py` | `cerebro/extensions/visual_similarity/visual_similarity.py` | Extension |
| `cerebro/core/safety/deletion_gate.py` | `cerebro/engine/deletion/deletion_gate.py` | Core |
| `cerebro/core/safety/trash_manager.py` | `cerebro/engine/deletion/trash_manager.py` | Core |
| `cerebro/core/fs_policy.py` | `cerebro/engine/discovery/fs_policy.py` | Core |
| `cerebro/core/preview.py` | `cerebro/services/preview.py` or `cerebro/utils/preview.py` | Keep |
| `cerebro/core/utils.py` | `cerebro/engine/_utils.py` or `cerebro/utils/core_utils.py` (no Qt/I/O at import) | Core |
| `cerebro/core/session.py` | `cerebro/experimental/session.py` | Experimental |
| `cerebro/core/scoring.py` | `cerebro/experimental/scoring.py` | Experimental |
| `cerebro/core/curation/scoring.py` | `cerebro/experimental/curation_scoring.py` | Experimental |
| `cerebro/ui/controllers/live_scan_controller.py` | `cerebro/controllers/live_scan_controller.py` | Core |

**History:** `cerebro/history/store.py` and `cerebro/history/models.py` **stay in place**. No move to services.

### B) Keep in place (no move)

| Path | Reason |
|------|--------|
| `main.py` | Entry; may later delegate to `cerebro.app.bootstrap` |
| `cerebro/__init__.py` | Package root |
| `cerebro/history/*` | First-class product capability; do not move under services |
| `cerebro/ui/**` (pages, widgets, components, theme_engine, state_bus, main_window) | UI layer unchanged except controllers move |
| `cerebro/workers/**` | Workers unchanged |
| `cerebro/services/*.py` | Services unchanged (no history/ here) |
| `cerebro/utils/**` | Utils unchanged; enforce strict rule (no Qt, no I/O at import) |
| `cerebro/ui/models/live_scan_snapshot.py` | Stays under ui/models |

### C) True duplicates — remove (do not move)

| Path | Reason |
|------|--------|
| `cerebro/ui/pages/models.py` | Duplicate of `history/models.py` → use `cerebro/history/models` or domain |
| `cerebro/ui/pages/store.py` | Duplicate of `history/store.py` → use `cerebro/history/store` |
| Second `ThemeMixin` class at end of `theme_engine.py` | In-file duplicate; delete block only |

### D) New files (create, no move)

| Path | Purpose |
|------|---------|
| `cerebro/app/application.py` | Application lifecycle wrapper |
| `cerebro/app/bootstrap.py` | Env, logging, crash handler, config |
| `cerebro/engine/pipeline/pipeline_contract.py` | ScanEngine protocol |
| `cerebro/scanners/__init__.py` | Scanner registry dict + re-exports |
| `cerebro/domain/__init__.py` | Re-export models |
| `cerebro/engine/**/__init__.py` | Per subpackage |
| `cerebro/extensions/**/__init__.py` | Per extension |
| `cerebro/experimental/__init__.py` | Re-export optional |

---

## 3) Required Import Rewrites (grep-style patterns)

- All previous patterns from the original plan still apply **except** History.
- **History:** Keep all imports as `from cerebro.history.store import` and `from cerebro.history.models import`. Do **not** introduce `cerebro.services.history`.
- **Reporting:** When moved to engine, use `from cerebro.engine.reporting.json_report import ...` etc.

(Remaining patterns unchanged: domain, engine pipeline/discovery/hashing/grouping/decision/deletion, scanners, controller, extensions/experimental.)

---

## 4) Risk List

- Unchanged from original plan, with these additions:
- **History:** Leaving `cerebro/history/` in place removes the risk of breaking pipeline and UI imports that reference `cerebro.history.store` and `cerebro.history.models`.
- **PipelineRequest mismatch:** `core/models.py` defines `PipelineRequest(scan_id, config)`; workers construct a different shape. Batch 1: patch only if it blocks runtime; Batch 2: full unification in domain (see Plan Corrections §2). Legacy ScanWorker may be non-authoritative until Batch 2; FastScanWorker is the active runtime path.
- **DeletionPolicy:** Two enums exist (core/models vs core/deletion). Canonical names are `MOVE_TO_TRASH` / `DELETE_PERMANENTLY`; domain (and in Batch 1, core/models) is single source of truth (see Plan Corrections §5).

---

## 5) Plan Corrections — Explicit Decisions

The following five items are **required** and must be reflected in implementation:

1. **Batch 1: Add `PipelineMode.SCAN` and `PipelineMode.DELETE`**  
   Make `PipelineMode` the authoritative workflow enum. Include `SCAN` and `DELETE` for runtime compatibility: `scan_worker` expects `PipelineMode.SCAN`, `delete_worker` expects `PipelineMode.DELETE`. Keep existing members (`EXACT`, `VISUAL`, `FUZZY`) temporarily. Later (v6 domain cleanup) this can split into `PipelineAction` (SCAN, DELETE) and `ScanStrategy` (EXACT, VISUAL, FUZZY).

2. **Batch 2: Unify `PipelineRequest`**  
   Today `core/models.py` defines `PipelineRequest(scan_id, config)` while `scan_worker` constructs `PipelineRequest(roots=..., mode=..., deletion_policy=..., ...)`. These are different shapes. Do not leave this implicit. In **Batch 2**, unify into a single authoritative request in `domain/models.py` shaped around actual worker usage (e.g. `roots`, `mode`, `deletion_policy`, optional `scan_id`/`config`). Keep shim compatibility if needed. **Plan note:** Legacy `ScanWorker` may remain non-authoritative until Batch 2; the active runtime path is **FastScanWorker**.

3. **Batch 1: Implement `get_cache_dir()` as a thin compatibility helper**  
   In `services/config.py`: `def get_cache_dir() -> str: return load_config().cache_dir`. If `load_config()` accepts a config path, keep default behavior simple and stable. This is a compatibility helper, not a new config system.

4. **Batch 1: Remove duplicate `ThemeMixin` block**  
   Remove the **second** `ThemeMixin` class in `theme_engine.py` at **lines ~1154–1162** (the one that references undefined `GEMINI_PALETTE`).

5. **Batch 1/2: Canonical `DeletionPolicy` names**  
   Choose explicit names as canonical: **`MOVE_TO_TRASH`**, **`DELETE_PERMANENTLY`** (not `TRASH`/`PERMANENT`). Clearer for logs, history, UI, and audit. **`domain/models.py`** (and in Batch 1, `core/models.py`) is the single source of truth; deletion engine and workers must use it. Add alias handling if needed (e.g. `POLICY_ALIASES = {"TRASH": MOVE_TO_TRASH, "PERMANENT": DELETE_PERMANENTLY}`) or update all usages directly if scope is small.

---

## 6) Revised Batch Plan (Feature-Preserving + Deletion Gate)

### Batch 1 — Boot stability ✅

- Fix syntax in `core/models.py`, `core/pipeline.py`.
- **Add `PipelineMode.SCAN` and `PipelineMode.DELETE`** to `core/models.py` for runtime compatibility (see Plan Corrections §1).
- **Choose canonical `DeletionPolicy`**: use `MOVE_TO_TRASH` / `DELETE_PERMANENTLY` as authoritative; normalize `core/deletion.py` and usages or add aliases (see Plan Corrections §5).
- Align `StartScanConfig.to_dict()` if needed.
- Add `requirements.txt` (PySide6, PyYAML, psutil, Pillow, send2trash).
- **Implement `get_cache_dir()`** in `services/config.py` as thin compatibility helper: `return load_config().cache_dir` (see Plan Corrections §3).
- Add stub `services/history_manager.py` with `get_history_manager()`.
- **Remove duplicate `ThemeMixin`** in `theme_engine.py` at lines ~1154–1162 (see Plan Corrections §4).
- **Check:** `main.py` runs, main window opens, scan and review pages open.

**Commit:** `stage1: boot stability and requirements`

---

### Batch 2 — Domain layer + shims ✅

- Create `cerebro/domain/` and `domain/__init__.py`.
- Copy `core/models.py` → `domain/models.py`; fix duplicate definitions.
- **Unify `PipelineRequest`** in `domain/models.py` to match actual worker/runtime usage (e.g. `roots`, `mode`, `deletion_policy`, optional `scan_id`/`config`). Keep shim compatibility if needed (see Plan Corrections §2). **Note:** Legacy ScanWorker may remain non-authoritative until this batch; active runtime path is FastScanWorker.
- Add shim in `core/models.py`: re-export from `cerebro.domain.models` so existing imports still work.
- **Check:** App runs, scan and delete still work.

**Commit:** `stage2: domain layer with core.models shim`

---

### Batch 3 — History move ❌ POSTPONED

- **Recommendation:** **Skip** moving History to `services/history/`.
- History remains at `cerebro/history/` as a first-class product capability.
- If a future change ever moves it, keep the package name `cerebro/history/` (do not place under services).
- **No commit for Batch 3** in the default plan.

---

### Batch 4 — Engine extraction + shims ✅

- Create `cerebro/engine/` and subpackages: `pipeline/`, `discovery/`, `hashing/`, `grouping/`, `decision/`, `deletion/`, `reporting/`.
- Copy (do not move yet) core engine modules into engine as in the move table; keep **reporting** under `engine/reporting/`.
- In each moved file, rewrite imports to use `cerebro.domain.models`, `cerebro.history` (unchanged), and sibling engine packages.
- Add `engine/pipeline/__init__.py` and export pipeline/domain types.
- Add shims in `core/` so existing `from cerebro.core.pipeline` etc. still resolve.
- **Check:** App runs, scan, review, cleanup (sanity only; deletion correctness is Gate A).

**Commit:** `stage4: engine layer with core shims`

---

### Gate A — Deletion correctness (release gate) ✅

**Must pass after Batch 4 and before Batch 5.**

**Definition of done:**

1. Files are actually **removed or moved to trash** on disk.
2. **Review UI** removes them immediately (no ghost groups).
3. **Next scan** does not rediscover those files.
4. **History/audit** reflects the actions accurately.

Treat deletion as a gate: do not proceed to scanner/controller shuffling (Batch 5) until this passes. Engine is the single source of truth for deletion after Batch 4; fix any bugs in pipeline → deletion_engine → history wiring here.

**Check:** Run app → scan small folder → open Review → delete a few files (trash) → confirm on disk and in UI → rescan same folder → confirm deleted files are gone from results; confirm history/audit shows the operations.

---

### Batch 5 — Scanners + controllers ✅

- **Proceed only after Gate A passes.**
- Create `cerebro/scanners/` and `cerebro/controllers/`.
- Move scanners and scanner_adapter as in move table; move `ui/controllers/live_scan_controller.py` → `controllers/live_scan_controller.py`.
- Unify scanner registry; update workers/pages to use registry + engine contract.
- **Check:** App runs, scan (simple/turbo) works.

**Commit:** `stage5: scanners and controllers moved`

---

### Batch 6 — Remove shims + quarantine dormant modules ✅

- Remove `core/` shims once all imports are migrated.
- Move dormant planned modules → `extensions/`.
- Move heavy/research modules → `experimental/`.
- Delete only true duplicates and artifacts (e.g. ui/pages/models.py, ui/pages/store.py).
- **Check:** Full run, all pages, scan + review + cleanup; tests if any.

**Commit:** `stage6: core removed, extensions and experimental in place`

---

## 7) Summary Table (Revised)

| Batch | Focus | Moves | Gate |
|-------|--------|-------|------|
| 1 | Boot + deps + stubs | None | — |
| 2 | Domain | Add domain, shim core.models | — |
| 3 | History | **Skipped** (history stays at cerebro/history/) | — |
| 4 | Engine | core → engine (copy + shim); reporting in engine | — |
| — | **Gate A** | **Deletion correctness** (must pass) | **Before Batch 5** |
| 5 | Scanners + controllers | scanners/, controllers/ | After Gate A |
| 6 | Cleanup | Remove shims; core → extensions/experimental | — |

---

## 8) Cursor Execution Instructions

**Universal rules for all batches:**

- **Branch:** Work only in `refactor/v6-architecture`.
- **Edit scope:** Small edits per run — **3–8 files** per batch run.
- **After each batch run:**
  1. **Launch app** (`python main.py` or equivalent).
  2. **Scan a small folder** (simple or turbo).
  3. **Open Review** and confirm results load.
  4. **After Gate A only:** **Delete** a few files (e.g. to trash), then **rescan** the same folder and confirm deleted files are gone and history/audit reflect the actions.

**Risk-control checklist (after each batch):**

- [ ] App launches.
- [ ] Scan page: start a scan (small folder).
- [ ] Review page: load result.
- [ ] (After Gate A) Delete and rescan; disk + UI + history/audit correct.
- [ ] Audit and Hub pages open without import/crash.
- [ ] Grep for `from cerebro.core.` and confirm only allowed shims or none.

---

End of revised plan.
