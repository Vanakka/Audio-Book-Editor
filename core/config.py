import copy
import base64
import binascii
import json
import logging
import math
import os
import tempfile

from core.app_paths import app_dir

logger = logging.getLogger(__name__)

APP_DIR = app_dir()
CONFIG_FILE = APP_DIR / "data" / "config.json"
LIBRARY_FILE = APP_DIR / "data" / "library.json"
CACHE_DIR = APP_DIR / "cache"
COVERS_DIR = CACHE_DIR / "covers"
METADATA_CACHE_DIR = CACHE_DIR / "metadata"

DEFAULT_CONFIG = {
    "last_root_folder": "",
    "libation_export_path": "",
    "rename_template": "{series}, Book {number}",
    "scraping_delay": 1.5,
    "scrapers_enabled": {
        "libation": True,
        "audible": True,
        "audible_api": True,
        "google_books": True,
        "openlibrary": True,
        "goodreads": True,
    },
    "theme": "Parchment",
    "show_book_number_in_title": True,
    "rename_file_on_save": False,
    "file_rename_template": "{series}, Book {number} [{identifier}]",
    "window_geometry": None,
    "splitter_sizes": None,
    "ffprobe_path": "",
    "ffmpeg_path": "",
}


class Config:
    def __init__(self):
        self._data = copy.deepcopy(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                if not isinstance(saved, dict):
                    raise ValueError("Settings must be a JSON object")
                for key, value in saved.items():
                    if key == "scrapers_enabled":
                        if isinstance(value, dict):
                            self._data[key].update({
                                name: enabled for name, enabled in value.items()
                                if name in DEFAULT_CONFIG[key] and isinstance(enabled, bool)
                            })
                    elif self._valid_value(key, value):
                        self._data[key] = value
            except (ValueError, OSError, UnicodeError) as e:
                logger.warning("Could not load config from %s: %s", CONFIG_FILE, e)

    @staticmethod
    def _valid_value(key, value):
        if key == "window_geometry":
            if value is None:
                return True
            if not isinstance(value, str):
                return False
            try:
                base64.b64decode(value.encode("ascii"), validate=True)
                return True
            except (ValueError, UnicodeError, binascii.Error):
                return False
        if key == "splitter_sizes":
            return value is None or (
                isinstance(value, list) and len(value) == 2
                and all(type(size) is int and 0 <= size <= 2 ** 31 - 1 for size in value)
            )
        if key == "scraping_delay":
            return type(value) in (int, float) and 0 <= value <= 10 and math.isfinite(value)
        default = DEFAULT_CONFIG.get(key)
        if isinstance(default, bool):
            return isinstance(value, bool)
        if isinstance(default, str):
            return isinstance(value, str)
        return key not in DEFAULT_CONFIG

    def save(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=CONFIG_FILE.parent,
                prefix=CONFIG_FILE.name + ".", suffix=".tmp", delete=False,
            ) as f:
                temp_file = f.name
                json.dump(self._data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_file, CONFIG_FILE)
        finally:
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value
