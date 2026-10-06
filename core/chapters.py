"""Helpers for safely constructing FFmetadata chapter files."""

import copy
import json
import os
import subprocess
import tempfile
from pathlib import Path
from fractions import Fraction

from mutagen.mp4 import MP4

from core.media_tools import media_tools_available, resolve_tool
from core.metadata import _file_write_lock


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


def _probe_media(file_path: str, option: str, timeout: int = 15) -> dict:
    """Read one ffprobe JSON section, raising a useful error on failure."""
    ffprobe = resolve_tool("ffprobe")
    if ffprobe is None:
        raise RuntimeError(
            "ffprobe was not found. Install FFmpeg and add it to PATH, "
            "or set the ffprobe path in Settings → Chapter tools."
        )
    result = subprocess.run(
        [ffprobe, "-v", "error", "-print_format", "json", option, file_path],
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")
    return json.loads(result.stdout or "{}")


def probe_chapters(file_path: str, timeout: int = 15) -> list[dict]:
    """Read chapter data with ffprobe, raising a useful error on failure."""
    return _probe_media(file_path, "-show_chapters", timeout).get("chapters", [])


def rewrite_chapters(file_path: str, chapters: list[dict], titles: list[str],
                     timeout: int = 120) -> bool:
    """Atomically replace chapter names while preserving all original streams/tags."""
    with _file_write_lock(file_path):
        return _rewrite_chapters_unlocked(file_path, chapters, titles, timeout)


def _rewrite_chapters_unlocked(file_path: str, chapters: list[dict], titles: list[str],
                               timeout: int) -> bool:
    available, missing = media_tools_available()
    if not available:
        raise RuntimeError(f"Missing required tools: {missing}; see README.md")

    metadata = build_ffmetadata(chapters, titles)
    original_tags = copy.deepcopy(MP4(file_path).tags)
    stream_maps = ["-map", "0"]
    for stream in _probe_media(file_path, "-show_streams").get("streams", []):
        # MP4 chapter text tracks are regenerated from the replacement chapter
        # table. Copying the old track can fail with an incompatible text tag.
        # Leave other data streams mapped rather than dropping all data.
        if (
            stream.get("codec_type") == "data"
            and stream.get("codec_name") == "bin_data"
            and stream.get("codec_tag_string") == "text"
            and stream.get("tags", {}).get("handler_name") == "SubtitleHandler"
            and type(stream.get("index")) is int
        ):
            stream_maps.extend(["-map", f"-0:{stream['index']}"])
    temp_output = ""
    metadata_path = ""
    try:
        # Reserve a unique output beside the original for atomic replacement;
        # only files created by this operation may be overwritten or removed.
        output_fd, temp_output = tempfile.mkstemp(
            prefix=f".{Path(file_path).stem}.", suffix=".tmp.m4b", dir=Path(file_path).parent
        )
        os.close(output_fd)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ffmetadata", delete=False, encoding="utf-8"
        ) as metadata_file:
            metadata_file.write(metadata)
            metadata_path = metadata_file.name

        ffmpeg = resolve_tool("ffmpeg")
        if ffmpeg is None:
            raise RuntimeError(
                "ffmpeg was not found. Install FFmpeg and add it to PATH, "
                "or set the ffmpeg path in Settings → Chapter tools."
            )

        result = subprocess.run(
            [
                ffmpeg, "-y", "-i", file_path, "-i", metadata_path,
                *stream_maps, "-map_metadata", "0", "-map_chapters", "1",
                "-c", "copy", temp_output,
            ],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr[-500:]}")

        output = MP4(temp_output)
        # FFmpeg does not retain every MP4 atom (including Tone freeform tags,
        # ASIN/CDEK and custom narrator/publisher tags). Restore the full tag
        # object, including Mutagen's retained unparsed atoms, before replacing.
        if original_tags is not None:
            output.tags = original_tags
            output.save()
        elif output.tags is not None:
            output.delete()
        MP4(temp_output)  # Validate again after restoring the tag atoms.
        rewritten_chapters = probe_chapters(temp_output)
        if len(rewritten_chapters) != len(chapters):
            raise RuntimeError("Chapter count changed during rewrite")
        for index, (before, after, title) in enumerate(zip(chapters, rewritten_chapters, titles)):
            expected_title = str(title or f"Chapter {index + 1}").replace("\r", " ").replace("\n", " ")
            if after.get("tags", {}).get("title") != expected_title:
                raise RuntimeError("Chapter title changed during rewrite")
            for key in ("start", "end"):
                before_time = Fraction(str(before.get(key, 0))) * Fraction(str(before.get("time_base", "1/1000")))
                after_time = Fraction(str(after.get(key, 0))) * Fraction(str(after.get("time_base", "1/1000")))
                if before_time != after_time:
                    raise RuntimeError("Chapter timing changed during rewrite")
        os.replace(temp_output, file_path)
        return True
    finally:
        if metadata_path and os.path.exists(metadata_path):
            os.unlink(metadata_path)
        if temp_output and os.path.exists(temp_output):
            os.unlink(temp_output)
