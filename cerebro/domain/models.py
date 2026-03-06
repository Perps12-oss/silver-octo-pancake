# cerebro/domain/models.py
"""
Authoritative source of shared domain models.
Unified: PipelineMode, DeletionPolicy, DeletionRequest, PipelineRequest.
Batch 2: compatibility with worker-style and legacy scan-style construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# PipelineMode — workflow (SCAN/DELETE) and scan strategy (EXACT/VISUAL/FUZZY)
# ---------------------------------------------------------------------------

class PipelineMode(str, Enum):
    SCAN = "scan"
    DELETE = "delete"
    EXACT = "exact"
    VISUAL = "visual"
    FUZZY = "fuzzy"


# ---------------------------------------------------------------------------
# DeletionPolicy — canonical naming
# ---------------------------------------------------------------------------

class DeletionPolicy(str, Enum):
    MOVE_TO_TRASH = "trash"
    DELETE_PERMANENTLY = "permanent"


# ---------------------------------------------------------------------------
# StartScanConfig — scan configuration (used by PipelineRequest legacy path)
# ---------------------------------------------------------------------------

@dataclass
class StartScanConfig:
    root: Path
    mode: PipelineMode = PipelineMode.EXACT
    min_size_bytes: int = 102_400  # 100 KB
    hash_bytes: int = 1024
    follow_symlinks: bool = False
    include_hidden: bool = False
    fast_mode: bool = True
    max_workers: int = 4
    allowed_extensions: Optional[List[str]] = None
    exclude_dirs: Optional[List[Path]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root": str(self.root),
            "mode": self.mode.value,
            "min_size_bytes": self.min_size_bytes,
            "hash_bytes": self.hash_bytes,
            "follow_symlinks": self.follow_symlinks,
            "include_hidden": self.include_hidden,
            "fast_mode": self.fast_mode,
            "max_workers": self.max_workers,
            "allowed_extensions": self.allowed_extensions,
            "exclude_dirs": [str(p) for p in self.exclude_dirs or []],
        }


# ---------------------------------------------------------------------------
# PipelineRequest — unified: worker-style (roots, mode, options) + legacy (scan_id, config)
# ---------------------------------------------------------------------------

@dataclass
class PipelineRequest:
    """
    Unified request for scan and delete pipelines.
    Supports worker-style construction (scan_worker, delete_worker) and
    legacy scan-style (scan_id + config). Optional fields preserve backward compat.
    """
    # Worker-style (scan_worker / delete_worker)
    roots: List[Path] = field(default_factory=list)
    mode: PipelineMode = PipelineMode.SCAN
    deletion_policy: Optional[DeletionPolicy] = None
    confirmation_token: str = ""
    dry_run: bool = False
    validation_mode: bool = False
    require_explicit_confirmation: bool = False
    options: Dict[str, Any] = field(default_factory=dict)

    # Legacy scan-style (scan_id + config)
    scan_id: Optional[str] = None
    config: Optional[StartScanConfig] = None

    # Optional legacy hooks (not used by pipeline.run; for compat)
    cancel_token: Any = None
    progress_cb: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scan_id": self.scan_id,
            "config": self.config.to_dict() if self.config else None,
            "roots": [str(p) for p in self.roots],
            "mode": self.mode.value,
            "deletion_policy": self.deletion_policy.value if self.deletion_policy else None,
            "options": dict(self.options),
        }

    def to_history_entry(self, name: str, engine_version: str) -> Any:
        """Legacy: build ScanHistoryEntry when config is present."""
        if self.config is None or self.scan_id is None:
            raise ValueError("PipelineRequest.to_history_entry requires scan_id and config")
        from cerebro.history.models import ScanHistoryEntry, ScanStatus
        return ScanHistoryEntry(
            scan_id=self.scan_id,
            name=name,
            root_path=str(self.config.root),
            status=ScanStatus.IN_PROGRESS,
            engine_version=engine_version,
            settings_snapshot=self.config.to_dict(),
        )


# ---------------------------------------------------------------------------
# DeletionRequest — engine-level context for deletion execution
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DeletionRequest:
    """Request context for deletion engine (policy + metadata)."""
    policy: DeletionPolicy
    metadata: Dict[str, Any] = field(default_factory=dict)


__all__ = [
    "PipelineMode",
    "DeletionPolicy",
    "StartScanConfig",
    "PipelineRequest",
    "DeletionRequest",
]
