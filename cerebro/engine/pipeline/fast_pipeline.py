# cerebro/engine/pipeline/fast_pipeline.py
"""
ULTRA-FAST duplicate scan pipeline (engine home).
Non-blocking UI, scandir discovery, size grouping, batched parallel hashing.
Uses cerebro.services.hash_cache for persistence.
"""

from __future__ import annotations

import os
import time
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from cerebro.services.hash_cache import HashCache, StatSignature

ProgressCB = Callable[[int, str, Dict[str, Any]], None]

MAX_WORKERS_LIMIT = 32


class _HashCache:
    """Backward-compatible adapter for HashCache (get/set_many by path, size, mtime)."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._cache = HashCache(self.db_path)

    def open(self) -> None:
        self._cache.open()

    def close(self) -> None:
        self._cache.close()

    def get(self, path: str, size: int, mtime: float) -> Optional[str]:
        try:
            sig = StatSignature(size=int(size), mtime_ns=int(float(mtime) * 1_000_000_000), dev=0, inode=0)
            return self._cache.get_quick(path, sig)
        except Exception:
            return None

    def set_many(self, rows: List[Tuple[str, int, float, str]]) -> None:
        try:
            batch = [
                (p, StatSignature(size=int(size), mtime_ns=int(float(mtime) * 1_000_000_000), dev=0, inode=0), str(qh))
                for p, size, mtime, qh in rows
            ]
            self._cache.set_quick_many(batch, algo="md5")
        except Exception:
            return


@dataclass(frozen=True, slots=True)
class FastFileInfo:
    path: str
    size: int
    mtime: float
    ext: str = ""


class FastDiscovery:
    """Very fast iterative directory scan using os.scandir (no recursion stack explosion)."""

    def scan(
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
    ) -> List[FastFileInfo]:
        out: List[FastFileInfo] = []
        stack: List[Path] = [Path(root)]
        last_report = 0
        # Report every 500 files so UI metrics update during discovery (was 5000).
        report_interval = 500

        while stack:
            if cancel_check():
                break

            cur = stack.pop()
            try:
                with os.scandir(cur) as it:
                    for entry in it:
                        if cancel_check():
                            break

                        name = entry.name
                        if not include_hidden and name.startswith("."):
                            continue

                        try:
                            if entry.is_dir(follow_symlinks=follow_symlinks):
                                if exclude_dirs and name in exclude_dirs:
                                    continue
                                stack.append(Path(entry.path))
                                continue

                            if not entry.is_file(follow_symlinks=follow_symlinks):
                                continue

                            st = entry.stat(follow_symlinks=follow_symlinks)
                            size = int(st.st_size)
                            if size < int(min_size):
                                continue

                            ext = os.path.splitext(name)[1].lower()
                            if allowed_exts and ext not in allowed_exts:
                                continue

                            out.append(
                                FastFileInfo(
                                    path=entry.path,
                                    size=size,
                                    mtime=float(st.st_mtime),
                                    ext=ext,
                                )
                            )
                            n = len(out)
                            if progress_callback and (n - last_report >= report_interval or n == 1):
                                progress_callback(n)
                                last_report = n
                        except Exception:
                            continue
            except Exception:
                continue

        if progress_callback and len(out) != last_report:
            progress_callback(len(out))
        return out

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
        chunk: List[FastFileInfo] = []
        stack: List[Path] = [Path(root)]
        last_report = 0
        report_interval = 500
        cumulative = 0

        while stack:
            if cancel_check():
                break

            cur = stack.pop()
            try:
                with os.scandir(cur) as it:
                    for entry in it:
                        if cancel_check():
                            break

                        name = entry.name
                        if not include_hidden and name.startswith("."):
                            continue

                        try:
                            if entry.is_dir(follow_symlinks=follow_symlinks):
                                if exclude_dirs and name in exclude_dirs:
                                    continue
                                stack.append(Path(entry.path))
                                continue

                            if not entry.is_file(follow_symlinks=follow_symlinks):
                                continue

                            st = entry.stat(follow_symlinks=follow_symlinks)
                            size = int(st.st_size)
                            if size < int(min_size):
                                continue

                            ext = os.path.splitext(name)[1].lower()
                            if allowed_exts and ext not in allowed_exts:
                                continue

                            chunk.append(
                                FastFileInfo(
                                    path=entry.path,
                                    size=size,
                                    mtime=float(st.st_mtime),
                                    ext=ext,
                                )
                            )
                            if len(chunk) >= chunk_size:
                                cumulative += len(chunk)
                                if progress_callback and (cumulative - last_report >= report_interval):
                                    progress_callback(cumulative)
                                    last_report = cumulative
                                yield chunk
                                chunk = []
                        except Exception:
                            continue
            except Exception:
                continue

        if chunk:
            cumulative += len(chunk)
            if progress_callback and cumulative != last_report:
                progress_callback(cumulative)
            yield chunk


class FastPipeline:
    """Main ultra-fast pipeline. Engine 'simple' = balanced; 'advanced' = more workers."""

    def __init__(
        self,
        max_workers: int = 0,
        cache_path: Optional[Path] = None,
        engine: str = "simple",
    ):
        import multiprocessing

        cpu = multiprocessing.cpu_count()
        base_workers = max(4, cpu * 2) if max_workers <= 0 else int(max_workers)
        self.engine = (engine or "simple").lower()
        if self.engine == "advanced":
            self.max_workers = min(MAX_WORKERS_LIMIT, base_workers * 2)
        else:
            self.max_workers = base_workers
        self.discovery = FastDiscovery()
        self._cancelled = False
        self.cache_path = cache_path

    def cancel(self) -> None:
        self._cancelled = True

    def run_fast_scan(
        self,
        root: Path,
        *,
        min_size: int = 1024,
        include_hidden: bool = False,
        follow_symlinks: bool = False,
        allowed_extensions: Optional[List[str]] = None,
        exclude_dirs: Optional[List[str]] = None,
        progress_cb: Optional[ProgressCB] = None,
        chunk_size: int = 10_000,
    ) -> Dict[str, Any]:
        start = time.time()
        self._cancelled = False

        def cancelled() -> bool:
            return bool(self._cancelled)

        def emit(pct: int, msg: str, meta: Dict[str, Any]):
            if progress_cb:
                progress_cb(int(max(0, min(100, pct))), msg, meta)

        emit(0, "FAST MODE: Discovering files…", {"phase": "discovering"})

        def discovery_progress(count: int) -> None:
            if progress_cb and not cancelled():
                pct = min(18, int(18 * min(1.0, count / max(1, 100_000))))
                progress_cb(
                    pct,
                    f"Discovering… {count:,} files",
                    {"phase": "discovering", "scanned_files": count},
                )

        allowed_exts = [e.lower() for e in (allowed_extensions or [])] or None
        files_count: int
        candidates: List[FastFileInfo]

        if chunk_size > 0:
            # Chunked path: never materialize full file list
            size_counts: Dict[int, int] = {}
            candidates = []
            files_count = 0
            for chunk in self.discovery.scan_chunked(
                Path(root),
                include_hidden=include_hidden,
                follow_symlinks=follow_symlinks,
                allowed_exts=allowed_exts,
                exclude_dirs=exclude_dirs,
                min_size=min_size,
                cancel_check=cancelled,
                progress_callback=discovery_progress,
                chunk_size=chunk_size,
            ):
                if cancelled():
                    return {"cancelled": True, "ok": False, "stats": {"scanned_files": files_count}}
                for f in chunk:
                    size_counts[f.size] = size_counts.get(f.size, 0) + 1
                for f in chunk:
                    if size_counts[f.size] > 1:
                        candidates.append(f)
                files_count += len(chunk)
        else:
            # Legacy path: full scan then size_map
            files = self.discovery.scan(
                Path(root),
                include_hidden=include_hidden,
                follow_symlinks=follow_symlinks,
                allowed_exts=allowed_exts,
                exclude_dirs=exclude_dirs,
                min_size=min_size,
                cancel_check=cancelled,
                progress_callback=discovery_progress,
            )
            files_count = len(files)
            if cancelled():
                return {"cancelled": True, "ok": False, "stats": {"scanned_files": files_count}}
            size_map: Dict[int, List[FastFileInfo]] = {}
            for f in files:
                size_map.setdefault(f.size, []).append(f)
            candidates = []
            for _, arr in size_map.items():
                if len(arr) > 1:
                    candidates.extend(arr)

        if cancelled():
            return {"cancelled": True, "ok": False, "stats": {"scanned_files": files_count}}

        emit(20, f"Grouping by size ({files_count:,} files)…", {"phase": "grouping", "scanned_files": files_count})
        emit(25, f"Hashing {len(candidates):,} candidates…", {"phase": "hashing", "scanned_files": files_count})

        cache = None
        if self.cache_path:
            try:
                cache = _HashCache(self.cache_path)
                cache.open()
            except Exception:
                cache = None

        try:
            t0 = time.time()
            total = len(candidates)
            done = 0
            # Phase 6C: only add to hash_groups when 2+ files share a hash; singletons go to pending and are discarded
            hash_groups: Dict[str, List[str]] = {}
            pending: Dict[str, str] = {}  # hash -> single path (promoted to hash_groups on second)

            def add_hash_result(h: str, path: str) -> None:
                if h in hash_groups:
                    hash_groups[h].append(path)
                elif h in pending:
                    first = pending.pop(h)
                    hash_groups[h] = [first, path]
                else:
                    pending[h] = path

            to_hash: List[FastFileInfo] = []
            cache_writes: List[Tuple[str, int, float, str]] = []

            if cache:
                for f in candidates:
                    qh = cache.get(f.path, f.size, f.mtime)
                    if qh:
                        add_hash_result(qh, f.path)
                    else:
                        to_hash.append(f)
            else:
                to_hash = candidates

            def emit_progress(done_count: int, stage_msg: str, current_path: str = ""):
                if not progress_cb:
                    return
                pct = 25 + int(65 * (done_count / max(1, total)))
                elapsed = max(0.001, time.time() - t0)
                rate = done_count / elapsed
                progress_cb(pct, stage_msg, {
                    "phase": "hashing",
                    "hashed": done_count,
                    "total": total,
                    "rate_fps": rate,
                    "scanned_files": files_count,
                    "current_path": current_path,
                    "current_file": current_path,
                    "elapsed_seconds": elapsed,
                })

            if progress_cb:
                emit_progress(0, f"Hashing {total:,} candidates…", "")

            with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
                for f, qh in ex.map(self._quick_hash_with_meta, to_hash, chunksize=64):
                    if cancelled():
                        break
                    done += 1
                    if qh:
                        add_hash_result(qh, f.path)
                        cache_writes.append((f.path, f.size, f.mtime, qh))
                    if progress_cb and (done % 256 == 0 or done == total):
                        emit_progress(done, f"Hashing… {done:,}/{total:,}", getattr(f, "path", "") or "")

            # Discard pending singletons (hash_groups now only has 2+ paths)
            del pending

            if cache and cache_writes:
                cache.set_many(cache_writes)

        finally:
            try:
                if cache:
                    cache.close()
            except Exception:
                pass

        if cancelled():
            return {"cancelled": True, "ok": False, "stats": {"scanned_files": files_count}}

        emit(92, "Finalizing results…", {"phase": "finalizing", "scanned_files": files_count})

        groups = []
        for h, paths in hash_groups.items():
            # Phase 6C: hash_groups only contains hashes with 2+ paths; no filter needed
            group = {"hash": h, "size": None, "paths": list(paths), "count": len(paths)}
            # Phase 7B: attach match_source per file; current-scan paths first
            group["files"] = [{"path": p, "match_source": "current_scan"} for p in paths]
            groups.append(group)

        # Phase 7B: enrich with indexed matches from global inventory (when enabled)
        try:
            use_inv = os.environ.get("CEREBRO_USE_INVENTORY", "1").strip().lower() not in ("0", "false", "no")
            if use_inv and root:
                from cerebro.services.global_inventory_db import get_global_inventory_db
                inv = get_global_inventory_db()
                current_device_id = inv.get_or_create_device(str(root))
                for group in groups:
                    qh = group.get("hash")
                    if not qh:
                        continue
                    indexed = inv.get_paths_by_hash(qh, exclude_device_ids={current_device_id})
                    for path, _dev_id, is_online in indexed:
                        group["paths"].append(path)
                        group["files"].append({
                            "path": path,
                            "match_source": "indexed_offline" if not is_online else "indexed",
                        })
                    group["count"] = len(group["paths"])
        except Exception:
            pass

        elapsed = time.time() - start
        emit(100, f"FAST MODE done: {len(groups)} duplicate groups", {
            "phase": "completed",
            "elapsed": elapsed,
            "elapsed_seconds": elapsed,
            "groups": len(groups),
            "groups_found": len(groups),
            "scanned_files": files_count,
        })

        return {
            "ok": True,
            "groups": groups,
            "groups_count": len(groups),
            "file_count": files_count,
            "stats": {
                "scanned_files": files_count,
                "candidates": len(candidates),
                "duplicate_groups": len(groups),
                "time_seconds": elapsed,
                "max_workers": self.max_workers,
            },
        }

    def _quick_hash_with_meta(self, f: FastFileInfo) -> Tuple[FastFileInfo, Optional[str]]:
        path = f.path
        try:
            size = f.size
            sample = 1 * 1024 * 1024

            if size <= 3 * sample:
                h = hashlib.md5()
                with open(path, "rb", buffering=0) as fp:
                    while True:
                        b = fp.read(1024 * 1024)
                        if not b:
                            break
                        h.update(b)
                return f, h.hexdigest()

            h = hashlib.md5()
            with open(path, "rb", buffering=0) as fp:
                h.update(fp.read(sample))
                mid = size // 2
                fp.seek(max(0, mid - sample // 2))
                h.update(fp.read(sample))
                fp.seek(max(0, size - sample))
                h.update(fp.read(sample))
            return f, h.hexdigest()
        except Exception:
            return f, None


__all__ = ["FastPipeline", "FastFileInfo", "FastDiscovery", "ProgressCB"]
