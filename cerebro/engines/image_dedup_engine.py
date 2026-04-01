"""
Image Deduplication Engine

Detects visually similar images using perceptual hashing (pHash + dHash).
Implements the BaseEngine interface with a four-stage pipeline:

  1. Discovery   — walk folders, collect image paths
  2. Hashing     — parallel pHash/dHash via Pillow + imagehash
  3. Clustering  — group images within a Hamming-distance threshold
  4. Ranking     — sort groups by similarity score, mark keepers

Similarity is measured as:
    score = 1.0 - (hamming_distance / hash_bits)

Requires:
    pip install Pillow imagehash
Optional (adds HEIC/RAW support):
    pip install pillow-heif rawpy
"""

from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from cerebro.engines.base_engine import (
    BaseEngine,
    DuplicateFile,
    DuplicateGroup,
    EngineOption,
    ScanProgress,
    ScanState,
)

# ---------------------------------------------------------------------------
# Image extension allowlist
# ---------------------------------------------------------------------------
IMAGE_EXTENSIONS: frozenset[str] = frozenset({
    ".jpg", ".jpeg", ".jfif",
    ".png", ".gif", ".bmp", ".webp",
    ".tiff", ".tif",
    ".heic", ".heif",
    ".avif",
    ".raw", ".cr2", ".cr3", ".nef", ".nrw",
    ".arw", ".srf", ".sr2",
    ".dng", ".orf", ".pef", ".rw2",
})

# pHash is 64 bits (8×8 DCT grid).  Hamming ≤ 10 ≈ 84% similar.
PHASH_BITS = 64


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

@dataclass
class _ImageEntry:
    path: Path
    size: int
    modified: float
    phash: Optional[int] = None     # integer form of pHash
    dhash: Optional[int] = None     # integer form of dHash
    width: int = 0
    height: int = 0
    fmt: str = ""
    error: Optional[str] = None


class _UnionFind:
    """Lightweight union-find for connected-component grouping."""

    def __init__(self) -> None:
        self._parent: Dict[int, int] = {}

    def find(self, x: int) -> int:
        if x not in self._parent:
            self._parent[x] = x
        if self._parent[x] != x:
            self._parent[x] = self.find(self._parent[x])
        return self._parent[x]

    def union(self, a: int, b: int) -> None:
        self._parent[self.find(a)] = self.find(b)

    def groups(self) -> Dict[int, List[int]]:
        result: Dict[int, List[int]] = {}
        for x in self._parent:
            root = self.find(x)
            result.setdefault(root, []).append(x)
        return result


def _hamming(a: int, b: int) -> int:
    """Count differing bits between two integers."""
    return bin(a ^ b).count("1")


def _load_image_entry(path: Path) -> _ImageEntry:
    """Load image metadata and compute pHash + dHash. Returns entry with error set on failure."""
    try:
        stat = path.stat()
    except OSError as exc:
        return _ImageEntry(path=path, size=0, modified=0.0, error=str(exc))

    entry = _ImageEntry(
        path=path,
        size=stat.st_size,
        modified=stat.st_mtime,
    )

    try:
        _open_image(entry)
    except Exception as exc:
        entry.error = str(exc)

    return entry


def _open_image(entry: _ImageEntry) -> None:
    """Open image and populate hash + metadata fields (modifies entry in-place)."""
    ext = entry.path.suffix.lower()

    # HEIC/HEIF via pillow-heif (optional)
    if ext in (".heic", ".heif"):
        try:
            import pillow_heif  # noqa: F401
            pillow_heif.register_heif_opener()
        except ImportError:
            entry.error = "pillow-heif not installed — HEIC/HEIF skipped"
            return

    # RAW formats via rawpy (optional)
    if ext in (".raw", ".cr2", ".cr3", ".nef", ".nrw", ".arw", ".srf",
               ".sr2", ".dng", ".orf", ".pef", ".rw2"):
        try:
            import rawpy  # type: ignore
            import numpy as np  # type: ignore
            from PIL import Image  # type: ignore
            with rawpy.imread(str(entry.path)) as raw:
                rgb = raw.postprocess(use_camera_wb=True, no_auto_bright=True,
                                      output_bps=8)
            img = Image.fromarray(rgb)
            entry.fmt = "RAW"
        except ImportError:
            entry.error = "rawpy not installed — RAW skipped"
            return
        except Exception as exc:
            entry.error = str(exc)
            return
    else:
        try:
            from PIL import Image  # type: ignore
            img = Image.open(entry.path).convert("RGB")
            entry.fmt = img.format or ext.lstrip(".").upper()
        except Exception as exc:
            entry.error = str(exc)
            return

    entry.width, entry.height = img.size

    try:
        import imagehash  # type: ignore
        entry.phash = int(imagehash.phash(img))
        entry.dhash = int(imagehash.dhash(img))
    except ImportError:
        entry.error = "imagehash not installed"
    except Exception as exc:
        entry.error = str(exc)
    finally:
        try:
            img.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class ImageDedupEngine(BaseEngine):
    """
    Perceptual image duplicate detector.

    Groups visually similar images using pHash + dHash with a configurable
    Hamming-distance threshold. Falls back gracefully if optional dependencies
    (imagehash, pillow-heif, rawpy) are absent.
    """

    def __init__(self) -> None:
        super().__init__()
        self._results: List[DuplicateGroup] = []
        self._progress = ScanProgress(state=ScanState.IDLE)
        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._scan_thread: Optional[threading.Thread] = None
        self._start_time: float = 0.0
        self._worker_pool: Optional[ThreadPoolExecutor] = None

        self._default_options: Dict = {
            "hash_algorithm": "phash",
            "similarity_threshold": 90,       # percent (0-100)
            "min_size_bytes": 0,
            "include_hidden": False,
            "follow_symlinks": False,
        }

    # ------------------------------------------------------------------ ABC

    def get_name(self) -> str:
        return "Image Deduplication"

    def get_mode_options(self) -> List[EngineOption]:
        return [
            EngineOption(
                name="hash_algorithm",
                display_name="Hash Algorithm",
                type="choice",
                default="phash",
                choices=["phash", "dhash", "phash+dhash"],
                tooltip="pHash (DCT-based) is best for rotated/scaled images. "
                        "dHash is faster. phash+dhash combines both for precision.",
            ),
            EngineOption(
                name="similarity_threshold",
                display_name="Similarity Threshold (%)",
                type="int",
                default=90,
                min_value=50,
                max_value=100,
                tooltip="Images with similarity ≥ this value are grouped together. "
                        "100 = pixel-identical. 90 = nearly identical (different EXIF/metadata).",
            ),
            EngineOption(
                name="min_size_bytes",
                display_name="Minimum File Size",
                type="int",
                default=0,
                min_value=0,
                max_value=500 * 1024 * 1024,
                tooltip="Skip images smaller than this size. 0 = no minimum.",
            ),
            EngineOption(
                name="include_hidden",
                display_name="Include Hidden Files",
                type="bool",
                default=False,
                tooltip="Include hidden files and directories.",
            ),
            EngineOption(
                name="follow_symlinks",
                display_name="Follow Symbolic Links",
                type="bool",
                default=False,
                tooltip="Follow symbolic links.",
            ),
        ]

    def configure(self, folders: List[Path], protected: List[Path],
                  options: Dict) -> None:
        self._folders = [Path(f) for f in folders]
        self._protected = [Path(p) for p in protected]
        merged = self._default_options.copy()
        merged.update(options)
        self._options = merged

    def start(self, progress_callback: Callable[[ScanProgress], None]) -> None:
        self._cancel_event.clear()
        self._pause_event.clear()
        self._progress = ScanProgress(state=ScanState.SCANNING)
        self._results = []
        self._start_time = time.time()

        max_workers = min(32, (os.cpu_count() or 4) * 4)
        self._worker_pool = ThreadPoolExecutor(max_workers=max_workers)

        self._scan_thread = threading.Thread(
            target=self._run_scan,
            args=(progress_callback,),
            daemon=True,
            name="ImageDedupScan",
        )
        self._scan_thread.start()

    def pause(self) -> None:
        if self._state == ScanState.SCANNING:
            self._pause_event.set()
            self._state = ScanState.PAUSED

    def resume(self) -> None:
        if self._state == ScanState.PAUSED:
            self._pause_event.clear()
            self._state = ScanState.SCANNING

    def cancel(self) -> None:
        self._cancel_event.set()
        self._pause_event.clear()
        self._state = ScanState.CANCELLED

    def get_results(self) -> List[DuplicateGroup]:
        return self._results

    def get_progress(self) -> ScanProgress:
        return self._progress

    # ------------------------------------------------------------------ pipeline

    def _run_scan(self, cb: Callable[[ScanProgress], None]) -> None:
        try:
            # Stage 1 — discover image files
            self._emit(cb, "Discovering image files…")
            paths = self._discover_images()
            if self._cancelled():
                return

            if not paths:
                self._finish(cb, files_scanned=0)
                return

            total = len(paths)
            self._emit(cb, f"Hashing {total:,} images…", files_scanned=total)

            # Stage 2 — compute hashes in parallel
            entries = self._compute_hashes(paths, cb)
            if self._cancelled():
                return

            # Stage 3 — cluster by similarity
            self._emit(cb, "Clustering similar images…", files_scanned=total)
            groups = self._cluster(entries)
            if self._cancelled():
                return

            # Stage 4 — build DuplicateGroup results
            self._emit(cb, "Building results…", files_scanned=total)
            self._build_results(groups)

            self._finish(
                cb,
                files_scanned=total,
                duplicates_found=sum(len(g.files) for g in self._results),
                groups_found=len(self._results),
                bytes_reclaimable=sum(g.reclaimable for g in self._results),
            )

        except Exception as exc:
            import traceback
            traceback.print_exc()
            self._progress = ScanProgress(
                state=ScanState.ERROR,
                current_file=f"Error: {exc}",
            )
            self._state = ScanState.ERROR
            cb(self._progress)
        finally:
            if self._worker_pool:
                self._worker_pool.shutdown(wait=False)

    # ------------------------------------------------------------------ stage 1

    def _discover_images(self) -> List[Path]:
        paths: List[Path] = []
        min_size = int(self._options.get("min_size_bytes", 0))
        include_hidden = bool(self._options.get("include_hidden", False))
        follow_links = bool(self._options.get("follow_symlinks", False))

        for folder in self._folders:
            if not folder.exists():
                continue
            for root, dirs, files in os.walk(folder, topdown=True,
                                              followlinks=follow_links):
                root_path = Path(root)
                if any(root_path.is_relative_to(p) for p in self._protected):
                    dirs[:] = []
                    continue
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith(".")]

                for name in files:
                    if self._cancelled():
                        return paths
                    if not include_hidden and name.startswith("."):
                        continue
                    if Path(name).suffix.lower() not in IMAGE_EXTENSIONS:
                        continue
                    fp = root_path / name
                    try:
                        if min_size and fp.stat().st_size < min_size:
                            continue
                    except OSError:
                        continue
                    paths.append(fp)

        return paths

    # ------------------------------------------------------------------ stage 2

    def _compute_hashes(
        self,
        paths: List[Path],
        cb: Callable[[ScanProgress], None],
    ) -> List[_ImageEntry]:
        """Hash all images in parallel; emit progress every 64 images."""
        total = len(paths)
        entries: List[_ImageEntry] = []
        done = 0
        lock = threading.Lock()

        futures = {
            self._worker_pool.submit(_load_image_entry, p): p
            for p in paths
        }

        for future in as_completed(futures):
            if self._cancelled():
                break
            self._check_pause()

            entry = future.result()
            with lock:
                entries.append(entry)
                done += 1
                if done % 64 == 0 or done == total:
                    pct = int(80 * done / max(1, total))   # 0-80% for hashing stage
                    self._progress = ScanProgress(
                        state=ScanState.SCANNING,
                        files_scanned=done,
                        elapsed_seconds=time.time() - self._start_time,
                        current_file=str(entry.path),
                    )
                    cb(self._progress)

        return entries

    # ------------------------------------------------------------------ stage 3

    def _cluster(self, entries: List[_ImageEntry]) -> Dict[int, List[_ImageEntry]]:
        """
        Group entries whose pHash (or dHash) is within the Hamming-distance
        threshold into connected components using Union-Find.

        Returns a dict: representative_index → [ImageEntry, ...]
        """
        threshold_pct = int(self._options.get("similarity_threshold", 90))
        max_dist = int(round(PHASH_BITS * (1.0 - threshold_pct / 100.0)))

        algo = str(self._options.get("hash_algorithm", "phash")).lower()

        # Only consider successfully hashed entries
        valid = [e for e in entries if e.phash is not None and e.error is None]
        n = len(valid)

        uf = _UnionFind()
        for i in range(n):
            uf.find(i)  # ensure all nodes exist

        # O(n²) comparison — acceptable up to ~5K images
        # For larger sets, bucket by prefix bits for O(n log n)
        for i in range(n):
            hi = valid[i].phash if algo != "dhash" else valid[i].dhash
            if hi is None:
                continue
            for j in range(i + 1, n):
                hj = valid[j].phash if algo != "dhash" else valid[j].dhash
                if hj is None:
                    continue
                dist = _hamming(hi, hj)
                if algo == "phash+dhash":
                    # Both hashes must agree
                    dh_i = valid[i].dhash
                    dh_j = valid[j].dhash
                    if dh_i is None or dh_j is None:
                        continue
                    dist = max(dist, _hamming(dh_i, dh_j))
                if dist <= max_dist:
                    uf.union(i, j)

        component_map = uf.groups()
        return {
            root: [valid[idx] for idx in indices]
            for root, indices in component_map.items()
            if len(indices) >= 2
        }

    # ------------------------------------------------------------------ stage 4

    def _build_results(
        self,
        groups: Dict[int, List[_ImageEntry]],
    ) -> None:
        """Convert clustered entries → DuplicateGroup list sorted by group size desc."""
        threshold_pct = int(self._options.get("similarity_threshold", 90))
        algo = str(self._options.get("hash_algorithm", "phash")).lower()

        result: List[DuplicateGroup] = []

        for group_id, (_, entries) in enumerate(
            sorted(groups.items(), key=lambda kv: -len(kv[1]))
        ):
            # Sort files within group: largest first (keeper)
            entries_sorted = sorted(entries, key=lambda e: e.size, reverse=True)
            keeper = entries_sorted[0]

            dup_files: List[DuplicateFile] = []
            for i, e in enumerate(entries_sorted):
                # Compute similarity to keeper
                k_hash = keeper.phash if algo != "dhash" else keeper.dhash
                e_hash = e.phash if algo != "dhash" else e.dhash
                if k_hash is not None and e_hash is not None:
                    dist = _hamming(k_hash, e_hash)
                    similarity = round(1.0 - dist / PHASH_BITS, 4)
                else:
                    similarity = 1.0 if i == 0 else 0.0

                dup_files.append(
                    DuplicateFile(
                        path=e.path,
                        size=e.size,
                        modified=e.modified,
                        extension=e.path.suffix.lower(),
                        is_keeper=(i == 0),
                        similarity=similarity,
                        metadata={
                            "width": e.width,
                            "height": e.height,
                            "format": e.fmt,
                            "megapixels": round(e.width * e.height / 1_000_000, 1)
                            if e.width and e.height else 0.0,
                        },
                    )
                )

            group = DuplicateGroup(group_id=group_id, files=dup_files)
            result.append(group)

        # Sort overall: groups with most reclaimable space first
        result.sort(key=lambda g: g.reclaimable, reverse=True)
        for new_id, g in enumerate(result):
            object.__setattr__(g, "group_id", new_id) if hasattr(g, "__dataclass_fields__") else setattr(g, "group_id", new_id)

        self._results = result

    # ------------------------------------------------------------------ helpers

    def _emit(
        self,
        cb: Callable[[ScanProgress], None],
        message: str,
        files_scanned: int = 0,
        duplicates_found: int = 0,
        groups_found: int = 0,
        bytes_reclaimable: int = 0,
    ) -> None:
        self._progress = ScanProgress(
            state=ScanState.SCANNING,
            files_scanned=files_scanned,
            duplicates_found=duplicates_found,
            groups_found=groups_found,
            bytes_reclaimable=bytes_reclaimable,
            elapsed_seconds=time.time() - self._start_time,
            current_file=message,
        )
        cb(self._progress)

    def _finish(
        self,
        cb: Callable[[ScanProgress], None],
        files_scanned: int = 0,
        duplicates_found: int = 0,
        groups_found: int = 0,
        bytes_reclaimable: int = 0,
    ) -> None:
        elapsed = time.time() - self._start_time
        self._progress = ScanProgress(
            state=ScanState.COMPLETED,
            files_scanned=files_scanned,
            duplicates_found=duplicates_found,
            groups_found=groups_found,
            bytes_reclaimable=bytes_reclaimable,
            elapsed_seconds=elapsed,
        )
        self._state = ScanState.COMPLETED
        cb(self._progress)

    def _cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def _check_pause(self) -> None:
        while self._pause_event.is_set() and not self._cancel_event.is_set():
            time.sleep(0.05)
