"""Post-build staging for the portable dist folder."""

from __future__ import annotations

import shutil
import sys
import argparse
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


def stage(dist_dir: Path = DIST_DIR) -> None:
    if not dist_dir.is_dir():
        raise SystemExit(f"Expected build output at {dist_dir}")

    for folder in ("data", "cache", "cache/covers", "cache/metadata", "tools/ffmpeg/bin"):
        (dist_dir / folder).mkdir(parents=True, exist_ok=True)

    tools = _find_ffmpeg_tools()
    bundled_dir = dist_dir / "tools" / "ffmpeg" / "bin"
    copied = []
    for name in ("ffmpeg", "ffprobe"):
        source = tools.get(name)
        if source and source.is_file():
            target = bundled_dir / source.name
            shutil.copy2(source, target)
            copied.append(target.name)

    readme = dist_dir / "PORTABLE-README.txt"
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
    print(f"Staged portable build at {dist_dir}")
    if copied:
        print("Bundled:", ", ".join(copied))
    else:
        print("Warning: FFmpeg binaries were not found on the build machine.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", type=Path, default=DIST_DIR)
    stage(parser.parse_args().dist_dir)
