# AudioBook Manager

## Setup

Use an isolated Python 3.12 environment so unrelated global packages cannot affect the app:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements-lock.txt
```

Run `launch.bat`; it automatically prefers `.venv` when present.

## Portable build

Package a self-contained copy that runs without Python installed on the target PC. The build writes only to subfolders and does not modify or overwrite source code.

### Build

```powershell
.\build-portable.ps1
```

This installs PyInstaller into `.venv` (if needed), bundles the app, and stages FFmpeg when it is found on the build machine. Build-only dependencies are listed in `requirements-build.txt`.

The build stops if installation, packaging, or staging fails. It refuses to replace a portable folder containing saved settings, logs, or cached covers. To build a fresh copy alongside it:

```powershell
.\build-portable.ps1 -DistRoot 'dist\fresh-build'
```

The result is `dist/fresh-build/AudioBook-Manager/`. Copy your existing `data/` and `cache/` into that folder after closing the app.

### Output locations

| Path | Purpose |
|------|---------|
| `dist/AudioBook-Manager/` | Portable app (~1.1 GB) — copy this folder to use or distribute |
| `build/audiobook-manager/` | PyInstaller scratch files (safe to delete and regenerate) |
| `core/`, `ui/`, `scrapers/`, etc. | **Not modified** by the build |

Both `dist/` and `build/audiobook-manager/` are gitignored.

### Portable folder layout

```
dist/AudioBook-Manager/
  AudioBook Manager.exe    ← run this
  _internal/               ← bundled Python + PySide6
  tools/ffmpeg/bin/        ← ffprobe + ffmpeg (copied at build time when available)
  data/                    ← settings and logs (populated on first run)
  cache/                   ← downloaded cover art
  PORTABLE-README.txt
```

### Using the portable build

Copy the entire `dist/AudioBook-Manager/` directory to a USB drive or another PC and run `AudioBook Manager.exe`. No Python, pip, or WinGet FFmpeg install is required on the target machine when FFmpeg was bundled during the build.

Writable data (`data/`, `cache/`) lives next to the executable, so settings travel with the folder. Re-run `build-portable.ps1` after source changes to produce a fresh portable copy.

### What still works / what is required

- **Works offline for local library work:** tag editing, rename/sort, chapter viewing and renaming (with bundled FFmpeg), Libation import.
- **Still needs network:** metadata fetch from Audible, Google Books, OpenLibrary, and Goodreads.
- **Not required on target PC:** Python 3.12, `.venv`, or a system FFmpeg install (if bundled at build time).

## Recent improvements

A code audit in June 2026 led to the following fixes:

- **Fetch error counts** — Batch fetch now reports one success or one error per book, even when several metadata providers fail for the same title.
- **Save on close** — Unsaved changes are written on a background worker thread instead of freezing the window while large M4B files are saved.
- **Faster library scan** — Embedded tags, ASIN/CDEK, and cover art are read from each file in a single open pass instead of three.
- **Window state** — Window size and left/right splitter position are remembered between sessions.
- **Detail panel structure** — The right-hand editor was split into tab modules under `ui/detail/` for easier maintenance.
- **Logging** — Errors and warnings are written to `data/app.log` (rotating) instead of being lost when the app is launched without a console.
- **Cover embedding** — Downloaded covers use the correct JPEG/PNG format when embedded into M4B files.
- **UI prototypes** — Standalone `mockup_*.py` files were moved to `mockups/`.
- **Tests** — Coverage includes single-file tag reads, per-book fetch accounting, and portable test discovery via `tests/__init__.py`.

The October 2026 audit repaired file collision handling, chapter rewrites, save/edit races, metadata matching, cover download limits, settings validation, and portable build safety. Runtime dependencies, including transitives, are pinned in `requirements-lock.txt`. See [the audit record](AUDIT-2026-10-05.md) for findings and verification.

## Chapter tools

The Chapters tab uses the same embedded chapter markers that Audiobook Shelf reads via `ffprobe`. Your M4B files already contain the data; the app must be able to find FFmpeg on your PC.

On first launch the app auto-detects `ffprobe` and `ffmpeg` from `PATH`, WinGet's FFmpeg install (`%LOCALAPPDATA%\Microsoft\WinGet\Links`), and other common locations. Discovered paths are saved to `data/config.json`. You can also set them manually under **Settings → Chapter tools**.

After installing FFmpeg, verify:

```powershell
ffprobe -version
ffmpeg -version
```

`launch.bat` prepends the WinGet FFmpeg folder to `PATH` when present. Chapter rewrites use a validated temporary M4B and atomically replace the original only after FFmpeg and Mutagen checks pass.

## Verification

```powershell
.venv\Scripts\python -m unittest discover -s tests -t . -v
.venv\Scripts\python -m compileall -q core scrapers ui tests main.py
.venv\Scripts\python -m pip check
```

Run these commands from the project root. From another working directory, pass absolute paths for both `-s` (the tests directory) and `-t` (the project root); `tests/__init__.py` adds the project root to `sys.path`.

## Logs

Runtime errors and warnings are recorded in `data/app.log`. If something fails silently in the GUI (a failed rename, cover download, or tag write), check that file first.
