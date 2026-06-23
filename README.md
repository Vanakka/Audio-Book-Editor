# AudioBook Manager

## Setup

Use an isolated Python 3.12 environment so unrelated global packages cannot affect the app:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements-lock.txt
```

Run `launch.bat`; it automatically prefers `.venv` when present.

## Chapter tools

Chapter reading and rewriting require both `ffprobe` and `ffmpeg` on `PATH`. After installing FFmpeg, verify:

```powershell
ffprobe -version
ffmpeg -version
```

The Chapters tab reports a clear dependency error when either command is unavailable. Chapter rewrites use a validated temporary M4B and atomically replace the original only after FFmpeg and Mutagen checks pass.

## Verification

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m compileall -q core scrapers ui tests main.py
.venv\Scripts\python -m pip check
```
