# Cleanup Manifest

This manifest defines files/folders moved to `_holding_cleanup_review/` for review.

## Keep (do not move)

- `cerebro/`
- `tests/`
- `main.py`
- `requirements.txt`
- `docs/HISTORY_FACADE_V2.md`

## Categories

### legacy_docs

- `CEREBRO_V2_UI_OVERHAUL.md`
- `CEREBRO_V2_IMPLEMENTATION_PLAN.md`
- `WINDOW_RESIZE_FIX.md`
- `RESUME_INSTRUCTIONS.md`
- `PHASE_1_PROGRESS.md`
- `PHASE_2_PROGRESS.md`
- `PHASE_3_PROGRESS.md`
- `INTEGRATION_STRATEGY.md`
- `EYE_CONTROLS_FIX.md`
- `AUDIT_HUB_REFACTOR.md`
- `docs/*.md` (all except `docs/HISTORY_FACADE_V2.md`)
- `docs/archive/UI_OVERHAUL_V6.md`
- `docs/read me/*.md`

### legacy_notes_txt

- `new plan.txt`
- `phase evolution.txt`
- `Cerebro_v2_Governance_Protocol L.txt`
- `Cerebro_v2_Phase_Tracker.txt`
- `Cerebro_v2_Ultimate_ValidatorTTT.txt`
- `Cerebro_v2_Ultimate_ValidatorTTTYUYU.txt`
- `Cerebro_v2_Ultimate_ValidatorTTTYUYUIOUIOIUIOO.txt`
- `docs/*.txt`
- `docs/read me/*.txt`

### state_artifacts

- `.omc/` (entire folder)

### generated_cache

- `.pytest_cache/` (entire folder)
- `cerebro/core/__pycache__/utils.cpython-314.pyc`
- `cerebro/core/reporting/__pycache__/__init__.cpython-314.pyc`
- `cerebro/core/reporting/__pycache__/json_report.cpython-314.pyc`
- `cerebro/core/safety/__pycache__/__init__.cpython-314.pyc`
- `cerebro/core/safety/__pycache__/deletion_gate.cpython-314.pyc`
- `cerebro/core/safety/__pycache__/trash_manager.cpython-314.pyc`
- `cerebro/core/scanners/__pycache__/__init__.cpython-314.pyc`
- `cerebro/core/scanners/__pycache__/advanced_scanner.cpython-314.pyc`
- `cerebro/core/scanners/__pycache__/simple_scanner.cpython-314.pyc`
- `cerebro/workers/__pycache__/fast_scan_worker.cpython-314.pyc`
