"""Post-build staging for the portable dist folder."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist" / "AudioBook-Manager"


def _find_ffmpeg_tools() -> dict[str, Path]:
    sys.path.insert(0, str(ROOT))
    from core.media_tools import auto_detect_tool_paths

    detected = auto_detect_tool_paths()
    tools: dict[str, Path] = {}
    for key, value in detected.items():
        if value:
            tools[key.replace("_path", "")] = Path(value)
    return tools


def stage() -> None:
    if not DIST_DIR.is_dir():
        raise SystemExit(f"Expected build output at {DIST_DIR}")

    for folder in ("data", "cache", "cache/covers", "cache/metadata", "tools/ffmpeg/bin"):
        (DIST_DIR / folder).mkdir(parents=True, exist_ok=True)

    tools = _find_ffmpeg_tools()
    bundled_dir = DIST_DIR / "tools" / "ffmpeg" / "bin"
    copied = []
    for name in ("ffmpeg", "ffprobe"):
        source = tools.get(name)
        if source and source.is_file():
            target = bundled_dir / source.name
            shutil.copy2(source, target)
            copied.append(target.name)

    readme = DIST_DIR / "PORTABLE-README.txt"
    ffmpeg_note = (
        "Bundled FFmpeg: " + ", ".join(copied)
        if copied
        else "FFmpeg was not bundled. Place ffprobe.exe and ffmpeg.exe in tools/ffmpeg/bin/"
    )
    readme.write_text(
        "\n".join([
            "AudioBook Manager (portable)",
            "",
            "Run: AudioBook Manager.exe",
            "",
            "Writable folders (safe to back up or move with this directory):",
            "  data/   settings and logs",
            "  cache/  downloaded cover art",
            "",
            ffmpeg_note,
            "",
            "This folder is self-contained. Your source code remains in the parent project directory.",
        ]),
        encoding="utf-8",
    )
    print(f"Staged portable build at {DIST_DIR}")
    if copied:
        print("Bundled:", ", ".join(copied))
    else:
        print("Warning: FFmpeg binaries were not found on the build machine.")


if __name__ == "__main__":
    stage()