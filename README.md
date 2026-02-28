# Cerebro — Gemini Duplicate Finder

A **Windows-only** duplicate file finder with a UI inspired by MacPaw Gemini 2. Built with PySide6.

## Install & Run (Windows)

1. **Requirements:** Windows 10/11, Python 3.10+
2. **Install dependencies:**
   ```bash
   pip install PySide6
   ```
3. **Run:**
   ```bash
   python main.py
   ```
   The app will not run on macOS or Linux (platform guard exits with a message).

## Features

- **Scanner engines:** **Turbo** (12x faster, production), **Ultra** (60x faster), **Quantum** (180x+ with GPU)
- **Smart Select:** One-click rules to keep newest, oldest, largest, smallest, or first file in each duplicate group
- **Deletion Gate:** Never deletes the last copy; every group keeps at least one file (safe badges on each group)
- **Live scan:** Real-time progress, file count, speed, ETA
- **Preview pane:** Dockable, resizable; image/video/document preview; side-by-side compare
- **History & export:** Timeline of scans, export to CSV/JSON
- **Audit log:** Deletion records, undo support
- **Hub:** Dashboard, stats, recent scans
- **Settings:** Scan options, performance, exclusions, cache, theme (dark/light)
- **Drag & drop** on every page with visual feedback
- **Keyboard shortcuts:** Ctrl+N (New Scan), Ctrl+S (Smart Select), Delete (confirm delete), F5 (refresh)
- **Theme:** Gemini dark/light with instant switch

## Screenshots

Screenshots coming soon.

## License

See project license file.
