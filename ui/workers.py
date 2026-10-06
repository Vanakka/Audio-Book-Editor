"""Background thread workers for long-running operations."""

import copy

from PySide6.QtCore import QThread, Signal, Slot

from core.models import AudioBook, MetadataResult
from core.scanner import scan_directory
from core.metadata import populate_book_from_tags, write_tags, write_cover


class ScanWorker(QThread):
    progress = Signal(int, int)  # current, total
    book_found = Signal(object)  # AudioBook
    finished_signal = Signal(list)  # all books

    def __init__(self, root_path: str, parent=None):
        super().__init__(parent)
        self.root_path = root_path
        self._cancelled = False

    def run(self):
        def on_progress(current, total):
            self.progress.emit(current, total)

        books = scan_directory(self.root_path, progress_callback=on_progress)

        # Read embedded tags for each book
        total = len(books)
        processed = []
        for i, book in enumerate(books):
            if self._cancelled:
                break
            populate_book_from_tags(book)
            processed.append(book)
            self.book_found.emit(book)
            self.progress.emit(i + 1, total)

        self.finished_signal.emit(processed)

    def cancel(self):
        self._cancelled = True


class FetchWorker(QThread):
    progress = Signal(int, int, str)  # current, total, book_title
    result = Signal(object, object)  # AudioBook, MetadataResult
    error = Signal(object, str)  # AudioBook, error_message
    finished_signal = Signal(int, int)

    def __init__(self, books: list[AudioBook], scrapers: list, parent=None):
        super().__init__(parent)
        self.books = books
        self.scrapers = scrapers
        self._cancelled = False

    def run(self):
        total = len(self.books)
        success = 0
        errors = 0
        for i, book in enumerate(self.books):
            if self._cancelled:
                break

            self.progress.emit(i + 1, total, book.display_title)

            book_success = False
            attempted = False
            for scraper in self.scrapers:
                if self._cancelled:
                    break
                if not scraper.supports_identifier_type(book.identifier_type):
                    continue
                attempted = True
                try:
                    result = scraper.fetch(
                        book.identifier,
                        book.identifier_type,
                        title_hint=book.title,
                        author_hint=book.author,
                    )
                    if result:
                        self.result.emit(book, result)
                        book_success = True
                        break
                except Exception as e:
                    self.error.emit(book, str(e))

            if book_success:
                success += 1
            elif attempted:
                errors += 1

        self.finished_signal.emit(success, errors)

    def cancel(self):
        self._cancelled = True


class SaveWorker(QThread):
    progress = Signal(int, int)
    finished_signal = Signal(int, int)  # success, errors
    book_saved = Signal(object)
    book_failed = Signal(object)

    def __init__(self, books: list[AudioBook], parent=None):
        super().__init__(parent)
        self.books = list(books)
        # Capture the submitted values before the UI can make further edits.
        # Mutagen snapshots only these copies after writing, never live editors.
        self._save_copies = {id(book): copy.deepcopy(book) for book in self.books}
        self._cancelled = False
        self.book_saved.connect(self._acknowledge_saved_book)

    @Slot(object)
    def _acknowledge_saved_book(self, book: AudioBook):
        """Update the saved baseline on the owning (UI) thread."""
        saved_book = self._save_copies[id(book)]
        book._original_values = dict(saved_book._original_values)
        book.check_modified()

    def run(self):
        success = 0
        errors = 0
        total = len(self.books)

        for i, book in enumerate(self.books):
            if self._cancelled:
                break
            self.progress.emit(i + 1, total)
            saved_book = self._save_copies[id(book)]
            if write_tags(saved_book):
                saved_book.snapshot()
                success += 1
                self.book_saved.emit(book)
            else:
                errors += 1
                self.book_failed.emit(book)

        self.finished_signal.emit(success, errors)

    def cancel(self):
        self._cancelled = True


class CoverDownloadWorker(QThread):
    progress = Signal(int, int, str)
    finished_signal = Signal(int, int)

    def __init__(self, books_and_urls: list[tuple[AudioBook, str]], parent=None):
        super().__init__(parent)
        self.books_and_urls = books_and_urls
        self._cancelled = False

    def run(self):
        from scrapers.cover_downloader import download_cover
        success = 0
        errors = 0
        total = len(self.books_and_urls)

        for i, (book, url) in enumerate(self.books_and_urls):
            if self._cancelled:
                break
            self.progress.emit(i + 1, total, book.display_title)

            cover_path = download_cover(
                url, book.identifier, source_key=book.file_path
            )
            if cover_path:
                try:
                    with open(cover_path, "rb") as f:
                        image_data = f.read()
                    image_format = (
                        "png" if cover_path.lower().endswith(".png") else "jpeg"
                    )
                    if write_cover(book, image_data, image_format):
                        success += 1
                    else:
                        errors += 1
                except Exception:
                    errors += 1
            else:
                errors += 1

        self.finished_signal.emit(success, errors)

    def cancel(self):
        self._cancelled = True


class FunctionWorker(QThread):
    """Run one callable off the UI thread and return its value or error."""
    result_ready = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, function, *args, parent=None, **kwargs):
        super().__init__(parent)
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self._cancelled = False

    def run(self):
        if self._cancelled:
            return
        try:
            result = self.function(*self.args, **self.kwargs)
            if not self._cancelled:
                self.result_ready.emit(result)
        except Exception as exc:
            if not self._cancelled:
                self.error_occurred.emit(str(exc))

    def cancel(self):
        self._cancelled = True
