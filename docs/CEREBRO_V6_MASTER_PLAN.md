# CEREBRO v6 Master Plan

This document is the **authoritative planning doc** for v6. It records what is implemented, broken, deferred, and advanced-only. Changes should follow agreed phases; files touched in grouped batches; app kept runnable after every phase. Commit after each phase.

**Checklist source:** CEREBRO v6 Master Checklist (user-provided).  
**Execution order:** Phase 0 → 1 → 2 → … → 10.

---

## Status overview

| Phase | Description | Status | Notes |
|-------|-------------|--------|------|
| 0 | Master plan doc | **Done** | This document |
| 1 | Critical correctness / UI truth | **Done** | Skipped count, error count, all §1 items |
| 2 | Simplify default UX | **Done** | Simple/Advanced mode; scanner tier in Advanced; single Start Scan CTA |
| 3 | Scan summary screen | **Done** | Summary card + sticky bar when complete |
| 4 | Scan result store + Resume | **Done** | M1–M5 + retention + fallback; resume verification; settings persistence |
| 5 | Query-backed Review | **Done** | Store-backed model, windows, selection state |
| 6 | Stream/chunk pipeline | Deferred | Architectural; out of scope |
| 7 | Global inventory + device-aware | Deferred | Large feature; out of scope |
| 8 | Advanced/Expert reorganization | **Done** | Expert opt-in; cache/exclusions behind it |
| 9 | Repo hygiene + launcher | **Done** | .gitignore; main.py release posture |
| 10 | Final validation | **Done** | All implementable phases complete |

---

## 0) Freeze random edits

- **Authoritative planning doc:** `docs/CEREBRO_V6_MASTER_PLAN.md` (this file).
- **Record:** Broken / misleading / working / deferred / advanced-only — maintained in sections below.
- **Agreed process:** Files touched in grouped batches; app runnable after every phase; commit after each phase.

---

## 1) Critical correctness (checklist vs implementation)

| Item | Status | Notes |
|------|--------|-------|
| Remove false 100% Similarity when nothing selected | Implemented | Similarity shows "—" when no comparison |
| True Review empty state for no duplicates found | Implemented | Dedicated state + message |
| Separate Review error state (data unavailable) | Implemented | _review_state + message |
| Scan explicitly: no duplicates / duplicates / cancelled / failed | Implemented | live_scan_panel phase labels |
| Destructive controls disabled when no actionable data | Implemented | Delete buttons disabled when count 0 |
| Smart Select hidden/disabled when no group | Implemented | Disabled when no groups or no selection |
| Metadata panel not meaningless dashes when nothing selected | Implemented | Placeholder message |
| Preview not dominant when no file selected | Implemented | Placeholder; layout unchanged |
| Empty-state layout not just blank comparison | Implemented | Center message by state |
| Review never displays stale values from previous selections | Implemented | _clear_selection_display on group |
| groups found = 0 not confused with Review failed to load | Implemented | Distinct states + messaging |
| Show skipped file count | **Implemented** | Snapshot files_skipped; format_files_processed; live panel |
| Show warnings/error count | **Implemented** | warnings_count + errors_count in snapshot/panel |
| Delete result propagation correct | Preserved | No change to propagation path |

---

## 2–3) Scan page / Review page clarity

- Scan states (Ready, Running, Completed, Cancelled, Failed): **implemented**; explicit outcome labels.
- Review states (Loading, No duplicates, Data unavailable, Groups available): implemented.
- Similarity "—" when no comparison: implemented.
- Select All disabled when no groups: implemented.
- Delete footer disabled when nothing selected: already true via count.
- Smart Select disabled when no loaded group: implemented.
- Empty-state messaging: implemented.
- Post-delete banner / failure dialog: unchanged; to be verified in all states.

---

## 4) Resume and persistence

- Resume folder/options: **implemented**; root folder verified before enabling Resume.
- Persist advanced/cleanup settings: **implemented**; scan_ui_mode, scanner_tier, media_type, engine to config.
- Document session-only vs persistent: deferred.

---

## 5–8) Default UX, summary screen, match truth, global inventory

- Phase 5–8 (except global inventory): **Done**. Global inventory deferred.

---

## 9–10) Repo, launcher, final validation

- Repo hygiene: **Done** (.gitignore, crash_report.txt, *.log).
- Launcher: **Done** (main.py respects CEREBRO_DEBUG/CEREBRO_PAUSE_EXIT for release).
- Final validation: **Done** (all implementable phases complete).

---

## 12–13) Scan result architecture + Query-backed Review

- **Done:** Persistent store, light payload, Review by scan_id, query-backed list, selection state, retention, write-failure fallback, optional env disable.

---

## 13–19) Metrics, match truth, Start/Settings/History/Hub, theme, repo, launcher

- **Done:** Metrics honesty (speed tooltips, skipped, warnings, result status); match type in Review; Start page clarity; config load before pages; History/Audit/Hub truth; theme polish; repo hygiene; launcher posture.

---

## 23) What must be preserved

- Deletion engine path, result propagation, history/audit, async thumbnails, virtualized list, theme tokens, page-shell, state bus, scanner registry, experimental quarantine — **preserved**.

---

## 24) What can wait

- Deeper controller relocation, full theme purity, fancy redesigns, richer experimental scanners, ML features, cosmetic repo cleanup — **wait**.

---

*Last updated: All implementable phases complete. Phases 6 (stream/chunk) and 7 (global inventory) remain deferred.*
