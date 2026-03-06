# cerebro/engine/pipeline/scan_engine.py
"""
Stable entrypoint for scan execution.
Delegates to FastPipeline; no logic redesign in this batch.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .fast_pipeline import FastPipeline, ProgressCB


class ScanEngine:
    """
    Stable entrypoint for running duplicate scans.
    Wraps FastPipeline; preserves current runtime behavior.
    """

    def __init__(
        self,
        max_workers: int = 0,
        cache_path: Optional[Path] = None,
        engine: str = "simple",
    ):
        path_or_none: Optional[Path] = Path(cache_path) if cache_path is not None else None
        self._pipeline = FastPipeline(
            max_workers=max_workers,
            cache_path=path_or_none,
            engine=engine,
        )

    def cancel(self) -> None:
        self._pipeline.cancel()

    def run_scan(
        self,
        root: Path,
        *,
        min_size: int = 1024,
        include_hidden: bool = False,
        follow_symlinks: bool = False,
        allowed_extensions: Optional[list] = None,
        exclude_dirs: Optional[list] = None,
        progress_cb: Optional[ProgressCB] = None,
    ) -> Dict[str, Any]:
        """Run fast duplicate scan. Delegates to FastPipeline.run_fast_scan."""
        return self._pipeline.run_fast_scan(
            Path(root),
            min_size=min_size,
            include_hidden=include_hidden,
            follow_symlinks=follow_symlinks,
            allowed_extensions=allowed_extensions,
            exclude_dirs=exclude_dirs,
            progress_cb=progress_cb,
        )


__all__ = ["ScanEngine"]
