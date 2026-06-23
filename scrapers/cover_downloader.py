"""Download and cache cover art images."""

from pathlib import Path

import requests
from PIL import Image
from io import BytesIO

from core.config import COVERS_DIR
from core.cache_keys import safe_cache_key
from core.metadata import MAX_COVER_BYTES, MAX_COVER_PIXELS
from scrapers.http import get_with_retry

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
    COVERS_DIR.mkdir(parents=True, exist_ok=True)

    # Return cached version if exists
    if cache_path.exists() and not force:
        return str(cache_path)

    try:
        resp = get_with_retry(
            url, requester=requests.get, headers=HEADERS, timeout=15
        )
        if len(resp.content) > MAX_COVER_BYTES:
            raise ValueError("Cover image exceeds 25 MB")

        # Verify it's a valid image
        img = Image.open(BytesIO(resp.content))
        if img.width * img.height > MAX_COVER_PIXELS:
            raise ValueError("Cover image has too many pixels")

        # Convert to RGB if needed (e.g., RGBA or palette)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Resize if too large
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.LANCZOS)

        temp_path = cache_path.with_suffix(".jpg.tmp")
        img.save(str(temp_path), "JPEG", quality=90)
        temp_path.replace(cache_path)
        return str(cache_path)

    except Exception as e:
        print(f"Failed to download cover from {url}: {e}")
        return None


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
