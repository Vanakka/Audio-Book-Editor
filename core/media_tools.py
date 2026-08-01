"""Locate ffprobe/ffmpeg for chapter tools."""

import logging
import os
import shutil
from pathlib import Path

from core.app_paths import app_dir

logger = logging.getLogger(__name__)

_TOOL_CACHE: dict[str, str | None] = {"ffprobe": None, "ffmpeg": None}
_PATH_OVERRIDES: dict[str, str] = {}


def _candidate_paths(tool: str) -> list[Path]:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    candidates = [
        app_dir() / "tools" / "ffmpeg" / "bin" / f"{tool}.exe",
        Path(local_app_data) / "Microsoft" / "WinGet" / "Links" / f"{tool}.exe",
        Path(program_files) / "ffmpeg" / "bin" / f"{tool}.exe",
        Path("C:/ffmpeg/bin") / f"{tool}.exe",
        Path("C:/tools/ffmpeg/bin") / f"{tool}.exe",
    ]
    packages_root = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
    if packages_root.is_dir():
        for match in packages_root.glob(f"**/{tool}.exe"):
            candidates.append(match)
    return candidates


def set_tool_paths(ffprobe_path: str = "", ffmpeg_path: str = "") -> None:
    """Apply explicit tool paths from settings (empty clears the override)."""
    _PATH_OVERRIDES["ffprobe"] = ffprobe_path.strip()
    _PATH_OVERRIDES["ffmpeg"] = ffmpeg_path.strip()
    _TOOL_CACHE["ffprobe"] = None
    _TOOL_CACHE["ffmpeg"] = None


def _is_executable(path: str) -> bool:
    return bool(path) and Path(path).is_file()


def resolve_tool(tool: str) -> str | None:
    """Return a usable path to ffprobe or ffmpeg, searching PATH and common installs."""
    if tool in _TOOL_CACHE and _TOOL_CACHE[tool] is not None:
        return _TOOL_CACHE[tool]

    override = _PATH_OVERRIDES.get(tool, "").strip()
    if _is_executable(override):
        _TOOL_CACHE[tool] = override
        return override

    found = shutil.which(tool)
    if found:
        _TOOL_CACHE[tool] = found
        return found

    for candidate in _candidate_paths(tool):
        if candidate.exists():
            resolved = str(candidate.resolve())
            _TOOL_CACHE[tool] = resolved
            logger.info("Resolved %s to %s", tool, resolved)
            return resolved

    if tool == "ffprobe":
        ffmpeg = resolve_tool("ffmpeg")
        if ffmpeg:
            sibling = Path(ffmpeg).with_name("ffprobe.exe")
            if sibling.is_file():
                resolved = str(sibling.resolve())
                _TOOL_CACHE["ffprobe"] = resolved
                return resolved

    _TOOL_CACHE[tool] = None
    return None


def media_tools_available() -> tuple[bool, str]:
    """Report whether both chapter command-line dependencies are installed."""
    missing = [name for name in ("ffprobe", "ffmpeg") if resolve_tool(name) is None]
    return (not missing, ", ".join(missing))


def auto_detect_tool_paths() -> dict[str, str]:
    """Return discovered ffprobe/ffmpeg paths without applying overrides."""
    detected = {}
    for tool in ("ffprobe", "ffmpeg"):
        _TOOL_CACHE[tool] = None
        resolved = resolve_tool(tool)
        if resolved:
            detected[f"{tool}_path"] = resolved
    return detected