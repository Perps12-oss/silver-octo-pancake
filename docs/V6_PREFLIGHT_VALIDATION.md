# CEREBRO v6 Preflight Validation Report

**Purpose:** Verify the repository against the updated plan before Batch 1 edits begin.  
**Plan reference:** `docs/V6_REFACTOR_MOVEMENT_PLAN.md`

---

## 1) PipelineMode compatibility

### Usages found

| Location | Usage |
|----------|--------|
| `cerebro/core/models.py` | `PipelineMode(str, Enum)` with **EXACT, VISUAL, FUZZY only**; `StartScanConfig.mode: PipelineMode = PipelineMode.EXACT` |
| `cerebro/workers/scan_worker.py` | `PipelineMode.SCAN` (line 39) — **not defined today → AttributeError if ScanWorker runs** |
| `cerebro/workers/delete_worker.py` | `PipelineMode.DELETE` (line 59) — **not defined today → AttributeError if DeleteWorker runs** |

### Code that assumes only EXACT/VISUAL/FUZZY

- **`core/models.py` line 32:** `mode: PipelineMode = PipelineMode.EXACT` — default only; adding SCAN/DELETE does not break this.
- **No** `if mode == PipelineMode.EXACT` (or VISUAL/FUZZY) branches found in workers, pipeline, or controllers.

**Preflight verdict:** Adding `PipelineMode.SCAN` and `PipelineMode.DELETE` in Batch 1 is safe. No code needs to be flagged for “expects only scan modes” other than the missing enum members themselves.

---

## 2) PipelineRequest mismatch

### Constructors / usages

| Location | What it does |
|----------|----------------|
| `core/models.py` | Defines `PipelineRequest(scan_id, config)` — two fields only. |
| `core/pipeline.py` | Defines a **different** `PipelineRequest` (lines 405+) with `config`, `cancel_token`, `progress_cb`, `**kwargs` for legacy compatibility. |
| `scan_worker.py` | Imports from `cerebro.core.models` and builds `PipelineRequest(roots=..., mode=..., deletion_policy=..., ...)` — **signature does not match models.PipelineRequest**; would raise at runtime if ScanWorker were used. |
| `delete_worker.py` | Imports from `cerebro.core.models` and builds `PipelineRequest(roots=[], mode=PipelineMode.DELETE, ...)` — same mismatch. |
| `core/grouping.py`, `hashing.py`, `clustering.py`, `decision.py` | Import `PipelineRequest` from `cerebro.core.pipeline` (the pipeline’s legacy class), not from models. |
| `core/visual_similarity.py`, `curation/scoring.py` | Import from `cerebro.core.models`. |
| `core/scanners/advanced_scanner.py`, `simple_scanner.py` | Type hints only for `PipelineRequest`. |

### Active runtime path (FastScanWorker)

- **FastScanWorker** does **not** use `PipelineRequest` from core at all. It uses a config dict and calls `FastPipeline.run_fast_scan()` or optimized scanners.
- **LiveScanController** instantiates only **FastScanWorker** (lines 75, 172, 182).
- **ScanPage** uses only **LiveScanController** and calls `_controller.start_scan(config)` (line 656); it never touches ScanWorker.

**Preflight verdict:** The active runtime path (ScanPage → LiveScanController → FastScanWorker) does **not** depend on the legacy `PipelineRequest` signature. Unifying `PipelineRequest` in Batch 2 is correct; no Batch 1 change required for PipelineRequest. Legacy ScanWorker remains broken until Batch 2; plan’s “FastScanWorker = authoritative, ScanWorker = legacy” is confirmed.

---

## 3) DeletionPolicy usage

### Definitions

| Location | Enum definition |
|----------|-----------------|
| `core/models.py` | `DeletionPolicy(str, Enum): MOVE_TO_TRASH = "trash", DELETE_PERMANENTLY = "permanent"` |
| `core/deletion.py` | `DeletionPolicy(Enum): TRASH = "trash", PERMANENT = "permanent"` |

### Usages

| Location | What it uses |
|----------|----------------|
| `core/pipeline.py` | Imports from **`.deletion`**; uses `DeletionPolicy.PERMANENT` and `DeletionPolicy.TRASH` (line 233). |
| `core/deletion.py` | Own enum; `can_handle()` and adapters use `DeletionPolicy.TRASH` and `DeletionPolicy.PERMANENT`. |
| `workers/cleanup_worker.py` | Imports from **`cerebro.core.models`**; uses `DeletionPolicy.MOVE_TO_TRASH`, `DeletionPolicy.DELETE_PERMANENTLY` — **already canonical**. |
| `workers/delete_worker.py` | Imports from **`cerebro.core.models`**; uses `DeletionPolicy.MOVE_TO_TRASH` (default) — **already canonical**. |
| `core/decision.py` | Imports from **`cerebro.core.pipeline`** (which re-exports from deletion); uses **`DeletionPolicy.DRY_RUN`** — **DRY_RUN is not defined** in either enum (pre-existing bug). |
| `review_page.py` | Uses string literals `MODE_TRASH = "trash"`, `MODE_PERMANENT = "permanent"` and `policy: {"mode": chosen_mode}`; no direct enum use — **safe**. |

### Batch 1 consolidation

- **core/deletion.py** must stop defining its own enum and use `cerebro.core.models.DeletionPolicy` (MOVE_TO_TRASH, DELETE_PERMANENTLY), and replace all TRASH/PERMANENT with those names.
- **core/pipeline.py** must use `DeletionPolicy.MOVE_TO_TRASH` and `DeletionPolicy.DELETE_PERMANENTLY` (either by importing from models or from deletion after deletion re-exports from models).
- **decision.py:** Uses `DeletionPolicy.DRY_RUN`, which does not exist in either enum. Either add DRY_RUN to the canonical enum in Batch 1/2 or fix decision.py later; otherwise that code path can raise AttributeError.

**Preflight verdict:** DeletionPolicy consolidation in Batch 1 requires editing **core/deletion.py** and **core/pipeline.py** so both use the canonical names from core/models. **core/deletion.py is an additional Batch 1 file.** decision.py’s use of DRY_RUN should be called out; add DRY_RUN to the canonical enum or defer decision.py.

---

## 4) ThemeMixin duplication

### Blocks in theme_engine.py

| Line range | Content |
|------------|---------|
| **1080–1110** | First `ThemeMixin`: compatibility mixin with `set_theme_engine`, `_on_theme_changed`, `apply_theme`, `get_theme_colors`. **Does not reference GEMINI_PALETTE.** |
| **1154–1162** | Second `ThemeMixin`: single method `theme_colors()` that returns `GEMINI_PALETTE.get(...)`. **Only this block references GEMINI_PALETTE** (undefined). |

**Preflight verdict:** Only the second block (lines 1154–1162) references GEMINI_PALETTE. Removing that block in Batch 1 is safe; the first ThemeMixin remains and is the one used by the rest of the codebase.

---

## 5) Worker runtime path

### ScanPage → controller → worker

- **ScanPage** (line 207): `_create_controller()` returns **LiveScanController**.
- **ScanPage** (line 656): `self._controller.start_scan(config)` — no ScanWorker.
- **LiveScanController** (lines 15, 75, 172, 182): imports and holds **FastScanWorker**; `start_scan` creates `FastScanWorker(config)`.

### Who uses ScanWorker

- **workers/__init__.py** exports ScanWorker (no internal use).
- **core/pipeline.py** line 308: comment only “(ScanWorker, FastScanWorker, LiveScanController)”.
- **core/scanners/simple_scanner.py** docstring says it is used by ScanWorker — but nothing in the UI or controllers instantiates ScanWorker.

**Preflight verdict:** ScanPage and LiveScanController use **only FastScanWorker**. No critical flow depends on ScanWorker; plan’s “FastScanWorker = authoritative, ScanWorker = legacy” is confirmed.

---

## 6) Batch 1 edit safety

### Six files originally listed

1. `cerebro/core/models.py`  
2. `cerebro/core/pipeline.py`  
3. `cerebro/services/config.py`  
4. `cerebro/services/history_manager.py` (new)  
5. `cerebro/ui/theme_engine.py`  
6. `requirements.txt`  

### Additional file required for Batch 1

- **`cerebro/core/deletion.py`** — Required so DeletionPolicy is consolidated: remove local `DeletionPolicy`, import from `cerebro.core.models`, and use `MOVE_TO_TRASH` / `DELETE_PERMANENTLY` everywhere. Otherwise pipeline continues to pass TRASH/PERMANENT and either deletion must understand both or pipeline must import from models and map; the clean approach is deletion using models’ enum.

### Optional / follow-up (not Batch 1)

- **`cerebro/core/decision.py`** — Uses `DeletionPolicy.DRY_RUN`, which is not defined. Either add DRY_RUN to the canonical enum in Batch 1 (or 2) or leave decision.py for a later batch and accept that the code path using it may fail until fixed.

### Summary: Batch 1 file list

| # | File | Purpose |
|---|------|---------|
| 1 | `cerebro/core/models.py` | Add PipelineMode.SCAN/DELETE; ensure DeletionPolicy canonical (MOVE_TO_TRASH, DELETE_PERMANENTLY); fix syntax / StartScanConfig.to_dict if needed. |
| 2 | `cerebro/core/pipeline.py` | Use canonical DeletionPolicy (MOVE_TO_TRASH, DELETE_PERMANENTLY); fix syntax if any. |
| 3 | `cerebro/core/deletion.py` | **Additional.** Import DeletionPolicy from core.models; replace TRASH → MOVE_TO_TRASH, PERMANENT → DELETE_PERMANENTLY. |
| 4 | `cerebro/services/config.py` | Add get_cache_dir() returning load_config().cache_dir. |
| 5 | `cerebro/services/history_manager.py` | **New.** Stub get_history_manager(). |
| 6 | `cerebro/ui/theme_engine.py` | Remove second ThemeMixin block (lines 1154–1162). |
| 7 | `requirements.txt` | Add PyYAML, psutil, Pillow, send2trash. |

**Total: 7 files** (6 edits + 1 new). Within “3–8 files” per run.

---

## Contradictions with the updated plan

1. **None.** Plan already states Batch 1 adds PipelineMode.SCAN/DELETE, canonical DeletionPolicy, get_cache_dir(), ThemeMixin removal, and Batch 2 unifies PipelineRequest; FastScanWorker is authoritative.
2. **DeletionPolicy consolidation scope:** Plan says “normalize all usages” and “deletion engine and workers must use it.” That implies **core/deletion.py** must be updated in Batch 1 so the deletion engine uses the same enum as models; the plan did not explicitly list deletion.py in the “first six files” — this preflight adds it.

---

## Confirmation: Batch 1 keeps the app runnable

- **PipelineMode:** Adding SCAN and DELETE does not remove or change EXACT/VISUAL/FUZZY; no branches found that would break.
- **DeletionPolicy:** Consolidating to MOVE_TO_TRASH/DELETE_PERMANENTLY with deletion.py and pipeline.py updated keeps behavior the same (same string values "trash"/"permanent"); review_page and UI already use strings.
- **get_cache_dir()** and **history_manager stub:** Additive; no existing code removed.
- **ThemeMixin removal:** Only the duplicate, broken block is removed; the first ThemeMixin remains.
- **requirements.txt:** Adding deps does not remove PySide6; app remains runnable if env is updated.
- **core/deletion.py:** Switching to models’ DeletionPolicy and renaming TRASH/PERMANENT to MOVE_TO_TRASH/DELETE_PERMANENTLY is a naming/import change only; behavior stays the same.

**Caveat:** If any code path in Batch 1 runs that uses `DeletionPolicy.DRY_RUN` (e.g. in decision.py), it will raise AttributeError until DRY_RUN is added to the canonical enum or that path is refactored. That is a pre-existing issue; Batch 1 can add DRY_RUN to models.DeletionPolicy if that path is in use, or leave it for Batch 2.

**Verdict:** Batch 1, with the seven files above (including core/deletion.py), is sufficient and keeps the app runnable provided DRY_RUN is either added to the canonical enum or the decision.py path is not exercised until fixed.
