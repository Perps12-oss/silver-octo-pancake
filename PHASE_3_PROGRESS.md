# Cerebro v2 — Phase 3 Progress

## Status: Phase 3 Complete ✅ | Ready for Phase 4

---

## Phase 3 — Image Dedup Engine + Preview Enhancements ✅ COMPLETE

**Goal:** Add perceptual image duplicate detection (pHash + dHash) and enhance
the preview panel with resolution/megapixel badges, format color-coding, and a
live pixel-diff overlay.

---

### New Files

| File | Lines | Description |
|------|-------|-------------|
| `cerebro/engines/image_dedup_engine.py` | ~380 | Full pHash+dHash engine |

---

### Files Modified

| File | Change Summary |
|------|---------------|
| `cerebro/engines/orchestrator.py` | Register `"photos"` → `ImageDedupEngine` |
| `cerebro/v2/ui/preview_panel.py` | Resolution+MP badge, format color badge, similarity %, diff strip |
| `cerebro/v2/ui/main_window.py` | Pass image metadata (width/height/format/MP/similarity) to preview dict |

---

### ImageDedupEngine — Pipeline

```
Stage 1  Discovery    Walk folders, collect IMAGE_EXTENSIONS files
Stage 2  Hashing      Parallel pHash + dHash via Pillow + imagehash
Stage 3  Clustering   Union-Find grouping by Hamming distance ≤ threshold
Stage 4  Ranking      Sort groups by reclaimable space; keeper = largest
```

**Optional deps (graceful fallback if absent):**
- `imagehash` — required for hashing
- `Pillow` — required
- `pillow-heif` — HEIC/HEIF support
- `rawpy` — RAW camera format support (CR2/NEF/ARW/DNG etc.)

**Supported extensions:** `.jpg .jpeg .jfif .png .gif .bmp .webp .tiff .tif
.heic .heif .avif .raw .cr2 .cr3 .nef .nrw .arw .srf .sr2 .dng .orf .pef .rw2`

**Options exposed to UI:**
| Option | Default | Range |
|--------|---------|-------|
| Hash Algorithm | `phash` | phash / dhash / phash+dhash |
| Similarity Threshold | 90% | 50–100% |
| Min File Size | 0 | 0–500 MB |
| Include Hidden | false | bool |
| Follow Symlinks | false | bool |

---

### Preview Panel Enhancements

#### Resolution + Megapixel Badge
- Shows `3 024 × 4 032 · 12.2 MP` for images with engine-provided metadata
- Falls back to `-- × --` for non-images

#### Format Color Badge
| Format | Color |
|--------|-------|
| JPEG/JPG | Orange `#e8825a` |
| PNG | Blue `#5a9ee8` |
| GIF | Purple `#a55ae8` |
| WEBP | Teal `#5ae8a4` |
| HEIC/HEIF | Yellow `#e8c25a` |
| RAW/CR2/NEF | Grey `#c8c8c8` |
| TIFF | Green `#8ae85a` |
| BMP | Red `#e85a5a` |

#### Similarity % Label
- Shows `96% similar` in accent cyan for image comparisons

#### Diff Overlay Strip
- Toggled by the "Diff Overlay" switch in the preview header
- When enabled: computes `PIL.ImageChops.difference(A, B)`, amplifies ×8,
  displays in a 120px strip below the side panels
- Automatically refreshes when A or B file changes while diff is on
- Uses a temporary file for canvas loading (cleaned up immediately)

---

## Phase 4 — Next Steps

**Goal:** Video & Music Dedup Engines

### Tasks
1. `cerebro/engines/video_dedup_engine.py`
   - FFmpeg frame extraction (sample N frames at 10%/50%/90% of duration)
   - pHash each frame, compare by cosine similarity of hash vectors
   - Register as `"videos"` mode

2. `cerebro/engines/music_dedup_engine.py`
   - ID3 tag fuzzy matching (title + artist ≥ 85% Levenshtein similarity)
   - Audio fingerprint via `chromaprint`/`acoustid` (optional)
   - Register as `"music"` mode

### Dependencies to Install
```bash
pip install mutagen  # ID3 tags (music mode)
# FFmpeg must be on PATH (video mode)
# Optional: pip install pyacoustid chromaprint-ctypes
```

---

## Summary

| Phase | Status | Files | Lines |
|-------|--------|-------|-------|
| Phase 0 | ✅ Complete | 6 | ~2 000 |
| Phase 1 | ✅ Complete | 11 | ~4 900 |
| Phase 2 | ✅ Complete | 3 modified | ~370 added |
| Phase 3 | ✅ Complete | 1 new + 3 modified | ~440 added |
| Phase 4 | 🔄 Next | — | — |

**Total progress: ~65% complete**

Two fully-functional scan modes now operational:
- **Files** — exact duplicate detection (SHA-256/MD5/Blake3)
- **Photos** — perceptual duplicate detection (pHash + dHash)
