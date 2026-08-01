"""Read and write M4B (MP4) metadata tags using mutagen."""

import logging
import os
import threading
from io import BytesIO
from pathlib import Path

from mutagen.mp4 import MP4, MP4Cover, MP4FreeForm, AtomDataType
from PIL import Image, UnidentifiedImageError

from core.cache_keys import safe_cache_key
from core.models import AudioBook, MetadataResult
from core.config import COVERS_DIR

logger = logging.getLogger(__name__)


_FILE_WRITE_LOCKS: dict[str, threading.RLock] = {}
_FILE_WRITE_LOCKS_GUARD = threading.Lock()


def _file_write_lock(file_path: str) -> threading.RLock:
    """Return the shared lock protecting mutations of one audiobook file."""
    key = os.path.normcase(os.path.realpath(os.path.abspath(file_path)))
    with _FILE_WRITE_LOCKS_GUARD:
        return _FILE_WRITE_LOCKS.setdefault(key, threading.RLock())

# Standard MP4 atom keys
TAG_MAP_READ = {
    "title": "\xa9nam",
    "author": "\xa9ART",
    "genre": "\xa9gen",
    "year": "\xa9day",
    "description": "\xa9cmt",
    "album": "\xa9alb",
}

# Keys that may appear as either standard or freeform depending on the tagger
# We try multiple key variants for each field
MULTI_KEY_READ = {
    "narrator": ["\xa9nrt", "\xa9wrt"],
    "publisher": ["\xa9pub", "----:com.pilabor.tone:PUBLISHER", "----:com.apple.iTunes:PUBLISHER"],
    "subtitle": [
        "----:com.pilabor.tone:SUBTITLE",
        "----:com.apple.iTunes:SUBTITLE",
    ],
    "language": [
        "----:com.pilabor.tone:LANGUAGE",
        "----:com.apple.iTunes:LANGUAGE",
    ],
    "series": [
        "----:com.pilabor.tone:SERIES",
        "----:com.apple.iTunes:SERIES",
    ],
    "series_number": [
        "----:com.pilabor.tone:PART",
        "----:com.apple.iTunes:PART",
    ],
    "asin": [
        "asin",
        "CDEK",
        "----:com.pilabor.tone:AUDIBLE_ASIN",
        "----:com.apple.iTunes:AUDIBLE_ASIN",
    ],
}

# Preferred keys for writing (use Tone format for freeform, standard keys where available)
WRITE_STANDARD = {
    "title": "\xa9nam",
    "author": "\xa9ART",
    "narrator": "\xa9nrt",
    "genre": "\xa9gen",
    "year": "\xa9day",
    "description": "\xa9cmt",
    "publisher": "\xa9pub",
}

WRITE_FREEFORM = {
    "subtitle": "----:com.pilabor.tone:SUBTITLE",
    "language": "----:com.pilabor.tone:LANGUAGE",
    "series": "----:com.pilabor.tone:SERIES",
    "series_number": "----:com.pilabor.tone:PART",
}

MAX_COVER_BYTES = 25 * 1024 * 1024
MAX_COVER_PIXELS = 40_000_000
MAX_COVER_DIMENSION = 2400


def _read_tag(tags, key: str) -> str:
    """Read a single tag value, handling both standard and freeform formats."""
    val = tags.get(key)
    if not val:
        return ""
    if isinstance(val, list):
        raw = val[0]
    else:
        raw = val
    if isinstance(raw, (bytes, MP4FreeForm)):
        return bytes(raw).decode("utf-8", errors="replace")
    return str(raw)


def _read_multi_key(tags, keys: list[str]) -> str:
    """Try multiple keys, return the first non-empty value."""
    for key in keys:
        val = _read_tag(tags, key)
        if val:
            return val
    return ""


def _read_tags_from_mp4(tags) -> MetadataResult:
    """Populate a MetadataResult from an already-open MP4 tag mapping."""
    result = MetadataResult(source="embedded")
    if not tags:
        return result

    for field, key in TAG_MAP_READ.items():
        setattr(result, field, _read_tag(tags, key))

    for field, keys in MULTI_KEY_READ.items():
        if field == "asin":
            continue
        setattr(result, field, _read_multi_key(tags, keys))

    return result


def read_tags(book: AudioBook) -> MetadataResult:
    """Read metadata from an M4B file into a MetadataResult."""
    try:
        mp4 = MP4(book.file_path)
    except Exception as e:
        logger.error("Error reading tags from %s: %s", book.file_path, e)
        return MetadataResult(source="embedded")

    return _read_tags_from_mp4(mp4.tags)


def populate_book_from_tags(book: AudioBook) -> bool:
    """Read embedded tags and populate the AudioBook fields. Returns True if tags found."""
    try:
        mp4 = MP4(book.file_path)
    except Exception as e:
        logger.error("Error opening %s for tag read: %s", book.file_path, e)
        book.snapshot()
        return False

    tags = mp4.tags or {}
    result = _read_tags_from_mp4(tags)

    book.title = result.title
    book.subtitle = result.subtitle
    book.author = result.author
    book.narrator = result.narrator
    book.series = result.series
    book.series_number = result.series_number
    book.description = result.description
    book.publisher = result.publisher
    book.year = result.year
    book.genre = result.genre
    book.language = result.language
    book.metadata_source = "embedded"

    book.asin_tag = _read_tag(tags, "asin") or _read_multi_key(
        tags, MULTI_KEY_READ.get("asin", [])
    )
    book.cdek_tag = _read_tag(tags, "CDEK")
    if not book.identifier and book.asin_tag:
        book.identifier = book.asin_tag
        book.identifier_type = "asin"

    if tags and "covr" in tags:
        try:
            book.has_embedded_cover = True
            _extract_cover(book, mp4)
        except Exception as e:
            logger.error("Error extracting cover from %s: %s", book.file_path, e)

    book.snapshot()
    return bool(result.title)


def _extract_cover(book: AudioBook, mp4: MP4):
    """Extract embedded cover art to the cache directory."""
    covers = mp4.tags.get("covr", [])
    if not covers:
        return

    cover_data = bytes(covers[0])
    ext = ".jpg"
    if covers[0].imageformat == MP4Cover.FORMAT_PNG:
        ext = ".png"

    cache_key = safe_cache_key(book.identifier, book.file_path)
    cover_path = COVERS_DIR / f"{cache_key}{ext}"
    cover_path.parent.mkdir(parents=True, exist_ok=True)

    with open(cover_path, "wb") as f:
        f.write(cover_data)

    book.cover_path = str(cover_path)


def extract_cover_bytes(book: AudioBook) -> bytes | None:
    """Get raw cover art bytes from M4B file."""
    try:
        mp4 = MP4(book.file_path)
        if mp4.tags and "covr" in mp4.tags:
            return bytes(mp4.tags["covr"][0])
    except Exception as e:
        logger.error("Error reading cover bytes: %s", e)
    return None


def write_tags(book: AudioBook) -> bool:
    """Write AudioBook metadata back to the M4B file. Returns True on success."""
    with _file_write_lock(book.file_path):
        return _write_tags_unlocked(book)


def _write_tags_unlocked(book: AudioBook) -> bool:
    try:
        mp4 = MP4(book.file_path)
        if mp4.tags is None:
            mp4.add_tags()
        tags = mp4.tags

        # Standard tags
        field_values = {
            "title": book.title,
            "author": book.author,
            "narrator": book.narrator,
            "genre": book.genre,
            "year": book.year,
            "description": book.description,
            "publisher": book.publisher,
        }
        for field, value in field_values.items():
            key = WRITE_STANDARD.get(field)
            if not key:
                continue
            if value:
                tags[key] = [value]
            elif key in tags:
                del tags[key]

        # Freeform tags
        for field, key in WRITE_FREEFORM.items():
            value = getattr(book, field, "")
            _write_freeform(tags, key, value)

        # ASIN / CDEK
        if book.asin_tag:
            tags["asin"] = [book.asin_tag]
            _write_freeform(tags, "----:com.pilabor.tone:AUDIBLE_ASIN", book.asin_tag)
        else:
            tags.pop("asin", None)
            tags.pop("----:com.pilabor.tone:AUDIBLE_ASIN", None)
        if book.cdek_tag:
            tags["CDEK"] = [book.cdek_tag]
        else:
            tags.pop("CDEK", None)

        mp4.save()
        book.snapshot()
        return True
    except Exception as e:
        logger.error("Error writing tags to %s: %s", book.file_path, e)
        return False


def _write_freeform(tags, key: str, value: str):
    """Write a freeform tag."""
    if value:
        tags[key] = [MP4FreeForm(value.encode("utf-8"), dataformat=AtomDataType.UTF8)]
    elif key in tags:
        del tags[key]


def write_cover(book: AudioBook, image_data: bytes, image_format: str = "jpeg") -> bool:
    """Embed cover art into the M4B file."""
    with _file_write_lock(book.file_path):
        return _write_cover_unlocked(book, image_data, image_format)


def _write_cover_unlocked(book: AudioBook, image_data: bytes, image_format: str) -> bool:
    try:
        image_data, image_format = _prepare_cover_bytes(image_data, image_format)
    except (ValueError, UnidentifiedImageError, OSError) as e:
        logger.warning("Invalid cover image: %s", e)
        return False

    try:
        mp4 = MP4(book.file_path)
        if mp4.tags is None:
            mp4.add_tags()

        fmt = MP4Cover.FORMAT_JPEG if image_format == "jpeg" else MP4Cover.FORMAT_PNG
        mp4.tags["covr"] = [MP4Cover(image_data, imageformat=fmt)]
        mp4.save()

        # Update cache
        ext = ".jpg" if image_format == "jpeg" else ".png"
        cache_key = safe_cache_key(book.identifier, book.file_path)
        cover_path = COVERS_DIR / f"{cache_key}{ext}"
        cover_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cover_path, "wb") as f:
            f.write(image_data)
        book.cover_path = str(cover_path)
        book.has_embedded_cover = True
        return True
    except Exception as e:
        logger.error("Error writing cover to %s: %s", book.file_path, e)
        return False


def _prepare_cover_bytes(image_data: bytes, preferred_format: str) -> tuple[bytes, str]:
    """Validate, resize, and normalize cover bytes for safe MP4 embedding."""
    if not image_data or len(image_data) > MAX_COVER_BYTES:
        raise ValueError("Cover image is empty or exceeds 25 MB")

    with Image.open(BytesIO(image_data)) as image:
        image.load()
        if image.width * image.height > MAX_COVER_PIXELS:
            raise ValueError("Cover image has too many pixels")
        image.thumbnail((MAX_COVER_DIMENSION, MAX_COVER_DIMENSION), Image.Resampling.LANCZOS)

        output = BytesIO()
        if preferred_format.lower() == "png":
            if image.mode not in ("RGB", "RGBA", "L", "LA"):
                image = image.convert("RGBA")
            image.save(output, "PNG", optimize=True)
            return output.getvalue(), "png"

        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.save(output, "JPEG", quality=90, optimize=True)
        return output.getvalue(), "jpeg"
