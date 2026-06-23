import os
import re
from pathlib import Path

from core.models import AudioBook

IDENTIFIER_RE = re.compile(r'\[([A-Za-z0-9]{10,13})\]')


def classify_identifier(identifier: str) -> str:
    if identifier.startswith("B0"):
        return "asin"
    if identifier.isdigit() and len(identifier) in (10, 13):
        return "isbn"
    if len(identifier) == 10 and identifier[:-1].isdigit() and identifier[-1] in "0123456789Xx":
        return "isbn"
    return "unknown"


def extract_identifier(filename: str) -> tuple[str, str]:
    match = IDENTIFIER_RE.search(filename)
    if match:
        ident = match.group(1)
        return ident, classify_identifier(ident)
    return "", "unknown"


def scan_directory(root_path: str, max_depth: int = 4, progress_callback=None) -> list[AudioBook]:
    """Scan a directory recursively for .m4b files, up to max_depth levels."""
    books = []
    root = Path(root_path)

    if not root.exists():
        return books

    m4b_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        depth = len(Path(dirpath).relative_to(root).parts)
        if depth >= max_depth:
            dirnames.clear()
            continue

        # Skip cache/data/resource directories
        dirnames[:] = [d for d in dirnames if d not in ('.Claude book tool', 'cache', 'data', '__pycache__')]

        for fname in filenames:
            if fname.lower().endswith('.m4b'):
                m4b_files.append((dirpath, fname))

    total = len(m4b_files)
    for i, (dirpath, fname) in enumerate(m4b_files):
        filepath = os.path.join(dirpath, fname)
        identifier, id_type = extract_identifier(fname)

        book = AudioBook(
            file_path=filepath,
            folder_path=dirpath,
            identifier=identifier,
            identifier_type=id_type,
        )
        books.append(book)

        if progress_callback:
            progress_callback(i + 1, total)

    # Sort by series then series_number (will be populated later), fallback to filename
    books.sort(key=lambda b: b.filename.lower())
    return books
