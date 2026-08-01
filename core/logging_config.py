"""Application-wide logging setup."""

import logging
from logging.handlers import RotatingFileHandler

from core.app_paths import app_dir

APP_DIR = app_dir()

LOG_FILE = APP_DIR / "data" / "app.log"
_CONFIGURED = False


def setup_logging() -> None:
    """Configure file logging once at application startup."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handler = RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root.addHandler(handler)
    _CONFIGURED = True