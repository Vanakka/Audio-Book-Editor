"""Helpers for safely constructing FFmetadata chapter files."""

import json
import os
import shutil
import subprocess
import tempfile

from mutagen.mp4 import MP4


def escape_ffmetadata_value(value: str) -> str:
    """Escape an FFmetadata value and keep it on one logical line."""
    value = str(value).replace("\r", " ").replace("\n", " ")
    value = value.replace("\\", "\\\\")
    for char in ("=", ";", "#"):
        value = value.replace(char, f"\\{char}")
    return value


def build_ffmetadata(chapters: list[dict], titles: list[str]) -> str:
    """Build a complete FFmetadata document for chapter names and timings."""
    if len(chapters) != len(titles):
        raise ValueError("Chapter and title counts do not match")

    lines = [";FFMETADATA1"]
    for index, (chapter, title) in enumerate(zip(chapters, titles)):
        lines.extend([
            "",
            "[CHAPTER]",
            f"TIMEBASE={chapter.get('time_base', '1/1000')}",
            f"START={chapter.get('start', '0')}",
            f"END={chapter.get('end', '0')}",
            f"title={escape_ffmetadata_value(title or f'Chapter {index + 1}')}",
        ])
    return "\n".join(lines) + "\n"


def media_tools_available() -> tuple[bool, str]:
    """Report whether both chapter command-line dependencies are installed."""
    missing = [name for name in ("ffprobe", "ffmpeg") if shutil.which(name) is None]
    return (not missing, ", ".join(missing))


def probe_chapters(file_path: str, timeout: int = 15) -> list[dict]:
    """Read chapter data with ffprobe, raising a useful error on failure."""
    if shutil.which("ffprobe") is None:
        raise RuntimeError("ffprobe is not installed; see README.md")
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_chapters", file_path],
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")
    return json.loads(result.stdout or "{}").get("chapters", [])


def rewrite_chapters(file_path: str, chapters: list[dict], titles: list[str],
                     timeout: int = 120) -> bool:
    """Atomically replace chapter names while preserving all original streams/tags."""
    available, missing = media_tools_available()
    if not available:
        raise RuntimeError(f"Missing required tools: {missing}; see README.md")

    metadata = build_ffmetadata(chapters, titles)
    temp_output = file_path + ".tmp.m4b"
    metadata_path = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ffmetadata", delete=False, encoding="utf-8"
        ) as metadata_file:
            metadata_file.write(metadata)
            metadata_path = metadata_file.name

        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", file_path, "-i", metadata_path,
                "-map", "0", "-map_metadata", "0", "-map_chapters", "1",
                "-c", "copy", temp_output,
            ],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr[-500:]}")

        MP4(temp_output)  # Validate the output container before replacement.
        if len(probe_chapters(temp_output)) != len(chapters):
            raise RuntimeError("Chapter count changed during rewrite")
        os.replace(temp_output, file_path)
        return True
    finally:
        if metadata_path and os.path.exists(metadata_path):
            os.unlink(metadata_path)
        if os.path.exists(temp_output):
            os.unlink(temp_output)
