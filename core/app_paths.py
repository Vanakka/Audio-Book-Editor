"""Resolve application, resource, and writable data directories."""

import sys
from pathlib import Path


def app_dir() -> Path:
    """Directory that should contain writable data/, cache/, and tools/."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def bundle_dir() -> Path:
    """Directory containing bundled read-only assets when frozen."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", app_dir()))
    return app_dir()


def resource_dir() -> Path:
    return bundle_dir() / "resources"