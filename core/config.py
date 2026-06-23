import json
import os
import copy
from pathlib import Path

APP_DIR = Path(__file__).parent.parent
CONFIG_FILE = APP_DIR / "data" / "config.json"
LIBRARY_FILE = APP_DIR / "data" / "library.json"
CACHE_DIR = APP_DIR / "cache"
COVERS_DIR = CACHE_DIR / "covers"
METADATA_CACHE_DIR = CACHE_DIR / "metadata"

DEFAULT_CONFIG = {
    "last_root_folder": "D:\\Audio-Books",
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
                scraper_settings = saved.pop("scrapers_enabled", None)
                self._data.update(saved)
                if isinstance(scraper_settings, dict):
                    self._data["scrapers_enabled"].update(scraper_settings)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp_file = CONFIG_FILE.with_suffix(CONFIG_FILE.suffix + ".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, CONFIG_FILE)

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value
