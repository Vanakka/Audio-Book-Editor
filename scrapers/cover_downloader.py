"""Download and cache cover art images."""

import logging
from contextlib import closing
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock

import requests
from PIL import Image

from core.config import COVERS_DIR
from core.cache_keys import safe_cache_key
from core.metadata import MAX_COVER_BYTES, MAX_COVER_PIXELS
from scrapers.http import get_with_retry

logger = logging.getLogger(__name__)
_CACHE_WRITE_LOCK = Lock()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def download_cover(url: str, identifier: str, max_size: int = 2400,
                   source_key: str = "", force: bool = False) -> str | None:
    """Download a cover image and cache it. Returns the local file path or None."""
    if not url:
        return None

    cache_key = safe_cache_key(identifier, source_key or url)
    cache_path = COVERS_DIR / f"{cache_key}.jpg"
    # Return cached version if exists
    if cache_path.exists() and not force:
        return str(cache_path)

    temp_path = None
    try:
        COVERS_DIR.mkdir(parents=True, exist_ok=True)
        with closing(get_with_retry(
            url, requester=requests.get, headers=HEADERS, timeout=15, stream=True,
        )) as resp:
            try:
                content_length = int(resp.headers.get("Content-Length", ""))
            except (TypeError, ValueError):
                content_length = 0
            if content_length > MAX_COVER_BYTES:
                raise ValueError("Cover image exceeds 25 MB")

            # Bound the body while downloading, including chunked responses.
            image_data = BytesIO()
            for chunk in resp.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                if image_data.tell() + len(chunk) > MAX_COVER_BYTES:
                    raise ValueError("Cover image exceeds 25 MB")
                image_data.write(chunk)

        image_data.seek(0)
        with Image.open(image_data) as source:
            if source.width * source.height > MAX_COVER_PIXELS:
                raise ValueError("Cover image has too many pixels")
            with source.convert("RGB") as img:
                if max(img.size) > max_size:
                    img.thumbnail((max_size, max_size), Image.LANCZOS)

                # Separate paths prevent concurrent downloads sharing a temp file.
                with NamedTemporaryFile(
                    prefix=f".{cache_key}.", suffix=".tmp", dir=COVERS_DIR, delete=False,
                ) as temporary:
                    temp_path = Path(temporary.name)
                img.save(str(temp_path), "JPEG", quality=90)
        # Windows can reject concurrent replacements of the same destination.
        with _CACHE_WRITE_LOCK:
            temp_path.replace(cache_path)
        return str(cache_path)

    except Exception as e:
        logger.error("Failed to download cover from %s: %s", url, e)
        return None
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError as e:
                logger.warning("Failed to remove temporary cover %s: %s", temp_path, e)


def get_cached_cover(identifier: str) -> str | None:
    """Get a cached cover image path if it exists."""
    cache_key = safe_cache_key(identifier, identifier)
    for ext in (".jpg", ".jpeg", ".png"):
        path = COVERS_DIR / f"{cache_key}{ext}"
        if path.exists():
            return str(path)
    return None


def clear_cache():
    """Remove all cached cover images."""
    if COVERS_DIR.exists():
        for f in COVERS_DIR.iterdir():
            if f.is_file():
                f.unlink()
