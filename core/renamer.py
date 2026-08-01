"""Folder/file rename and sort logic with dry-run preview and safety checks."""

import logging
import os
import re
import shutil
from pathlib import Path

from core.models import AudioBook

logger = logging.getLogger(__name__)

TEMPLATES = [
    ("Series, Book #", "{series}, Book {number}"),
    ("Series - Book #", "{series} - Book {number}"),
    ("Author - Title", "{author} - {title}"),
    ("Title [ASIN]", "{title} [{identifier}]"),
    ("Series Book # - Title", "{series} Book {number} - {title}"),
]

# Characters not allowed in Windows filenames
INVALID_CHARS = re.compile(r'[<>:"/\\|?*]')


def _sanitize_filename(name: str) -> str:
    """Remove or replace characters invalid in Windows filenames."""
    name = INVALID_CHARS.sub('', name)
    name = name.strip('. ')
    # Limit length
    if len(name) > 200:
        name = name[:200]
    return name


def _format_template(book: AudioBook, template: str) -> str:
    """Apply a naming template to a book."""
    replacements = {
        "{title}": book.title or "Unknown Title",
        "{author}": book.author or "Unknown Author",
        "{narrator}": book.narrator or "",
        "{series}": book.series or "Standalone",
        "{number}": book.series_number or "0",
        "{year}": book.year or "",
        "{identifier}": book.identifier or "",
        "{publisher}": book.publisher or "",
    }
    result = template
    for key, val in replacements.items():
        result = result.replace(key, val)

    return _sanitize_filename(result)


def preview_renames(books: list[AudioBook], template: str) -> list[tuple[AudioBook, str, str, bool]]:
    """Preview rename operations. Returns list of (book, old_name, new_name, has_conflict)."""
    previews = []
    seen_names = {}

    for book in books:
        old_name = Path(book.folder_path).name
        new_name = _format_template(book, template)

        if not new_name:
            new_name = old_name

        # Check for conflicts
        parent = str(Path(book.folder_path).parent)
        key = (parent, new_name.lower())
        conflict = False

        if key in seen_names:
            conflict = True
        elif new_name != old_name:
            new_path = Path(book.folder_path).parent / new_name
            if new_path.exists():
                conflict = True

        seen_names[key] = book
        previews.append((book, old_name, new_name, conflict))

    return previews


def execute_renames(books: list[AudioBook], template: str) -> tuple[int, int]:
    """Execute rename operations. Returns (success_count, error_count)."""
    previews = preview_renames(books, template)
    success = 0
    errors = 0

    for book, old_name, new_name, conflict in previews:
        if conflict or old_name == new_name:
            continue

        old_path = Path(book.folder_path)
        new_path = old_path.parent / new_name

        try:
            os.rename(str(old_path), str(new_path))

            # Update book paths
            old_file = Path(book.file_path)
            new_file_path = new_path / old_file.name
            book.folder_path = str(new_path)
            book.file_path = str(new_file_path)

            success += 1
        except OSError as e:
            logger.error("Failed to rename %s -> %s: %s", old_path, new_path, e)
            errors += 1

    return success, errors


def rename_file(book: AudioBook, template: str) -> bool:
    """Rename a single M4B file based on a template. Returns True on success."""
    new_name = _format_template(book, template) + ".m4b"
    return rename_to_filename(book, new_name)


def rename_to_filename(book: AudioBook, new_name: str) -> bool:
    """Safely rename one M4B and its companion cue within the same folder."""
    new_name = new_name.strip()
    if not new_name:
        return False
    if not new_name.lower().endswith(".m4b"):
        new_name += ".m4b"

    if Path(new_name).name != new_name or _sanitize_filename(Path(new_name).stem) != Path(new_name).stem:
        logger.warning("Cannot rename: invalid filename %r", new_name)
        return False

    old_path = Path(book.file_path)

    if old_path.name == new_name:
        return True  # Already correct

    new_path = old_path.parent / new_name
    old_cue = old_path.with_suffix(".cue")
    new_cue = new_path.with_suffix(".cue")

    if new_path.exists() and new_path != old_path:
        logger.warning("Cannot rename: %s already exists", new_path)
        return False
    if old_cue.exists() and new_cue.exists() and new_cue != old_cue:
        logger.warning("Cannot rename: %s already exists", new_cue)
        return False

    try:
        os.rename(str(old_path), str(new_path))
        if old_cue.exists():
            try:
                os.rename(str(old_cue), str(new_cue))
            except OSError:
                os.rename(str(new_path), str(old_path))
                raise

        book.file_path = str(new_path)
        return True
    except OSError as e:
        logger.error("Failed to rename file %s -> %s: %s", old_path.name, new_name, e)
        return False


def group_by_series(books: list[AudioBook]) -> tuple[dict[str, list[AudioBook]], list[AudioBook]]:
    """Group books by series name. Returns (series_map, no_series_list)."""
    series_map: dict[str, list[AudioBook]] = {}
    no_series: list[AudioBook] = []
    for book in books:
        if book.series:
            series_map.setdefault(book.series, []).append(book)
        else:
            no_series.append(book)
    # Sort each series by book number
    for series in series_map.values():
        series.sort(key=lambda b: _sort_number(b.series_number))
    return series_map, no_series


def _sort_number(num_str: str) -> float:
    """Convert series number string to sortable float."""
    try:
        # Handle "1-2" format
        if "-" in num_str:
            return float(num_str.split("-")[0])
        return float(num_str)
    except (ValueError, TypeError):
        return 99999


def preview_sort(books: list[AudioBook], dest_root: str,
                 series_config: dict[str, str],
                 standalone_config: dict[str, str] = None) -> list[tuple[AudioBook, str, str, bool]]:
    """Preview sort operations.

    Args:
        books: All books to consider
        dest_root: Destination root folder
        series_config: {series_name: "Ongoing"/"Complete"/"Skip"}
        standalone_config: {file_path: folder_name} for no-series books
                          folder_name can be "Standalone" or a genre name

    Returns: list of (book, old_path, new_path, has_conflict)
    """
    previews = []
    standalone_config = standalone_config or {}
    seen_paths = set()

    for book in books:
        if book.series:
            status = series_config.get(book.series, "Skip")
            if status == "Skip":
                continue
            folder_name = f"{book.series} {status}"
        elif book.file_path in standalone_config:
            folder_name = standalone_config[book.file_path]
        else:
            continue  # Skip this book

        # Sanitize folder name
        folder_name = INVALID_CHARS.sub('', folder_name).strip('. ')

        new_folder = os.path.join(dest_root, folder_name)
        old_path = book.file_path
        new_path = os.path.join(new_folder, Path(old_path).name)

        # Skip if already in the right place
        if os.path.normpath(old_path) == os.path.normpath(new_path):
            continue

        # Check for conflicts
        conflict = False
        norm_new = os.path.normpath(new_path).lower()
        if norm_new in seen_paths:
            conflict = True
        elif os.path.exists(new_path):
            conflict = True
        else:
            old_cue = Path(old_path).with_suffix(".cue")
            new_cue = Path(new_path).with_suffix(".cue")
            if old_cue.exists() and new_cue.exists():
                conflict = True
        seen_paths.add(norm_new)

        previews.append((book, old_path, new_path, conflict))

    return previews


def execute_sort(previews: list[tuple[AudioBook, str, str, bool]]) -> tuple[int, int]:
    """Execute sort operations. Returns (success_count, error_count)."""
    success = 0
    errors = 0

    for book, old_path, new_path, conflict in previews:
        if conflict:
            errors += 1
            continue

        try:
            # Create destination folder
            os.makedirs(os.path.dirname(new_path), exist_ok=True)

            # Move the m4b and companion cue as one logical operation.
            old_cue = Path(old_path).with_suffix(".cue")
            new_cue = Path(new_path).with_suffix(".cue")
            if old_cue.exists() and new_cue.exists():
                raise shutil.Error(f"Companion cue already exists: {new_cue}")

            shutil.move(old_path, new_path)
            if old_cue.exists():
                try:
                    shutil.move(str(old_cue), str(new_cue))
                except (OSError, shutil.Error):
                    shutil.move(new_path, old_path)
                    raise

            # Update book paths
            book.file_path = new_path
            book.folder_path = os.path.dirname(new_path)

            # Clean up empty source folder
            old_folder = os.path.dirname(old_path)
            try:
                if not os.listdir(old_folder):
                    os.rmdir(old_folder)
            except OSError:
                pass

            success += 1
        except (OSError, shutil.Error) as e:
            logger.error("Failed to move %s -> %s: %s", old_path, new_path, e)
            errors += 1

    return success, errors
