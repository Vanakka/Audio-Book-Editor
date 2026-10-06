"""Main application window."""

import base64
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QToolBar, QStatusBar, QFileDialog,
    QMessageBox, QApplication,
)
from PySide6.QtCore import Qt, QSize, QThread, QEventLoop, QByteArray
from PySide6.QtGui import QAction, QKeySequence

from core.config import Config
from core.media_tools import set_tool_paths
from core.models import AudioBook, MetadataResult
from core.renamer import rename_file
from core.libation_import import parse_libation_export
from scrapers.audible import AudibleScraper
from scrapers.google_books import GoogleBooksScraper
from scrapers.openlibrary import OpenLibraryScraper
from scrapers.goodreads import GoodreadsScraper
from scrapers.audible_api import AudibleAPIScraper
from ui.sort_dialog import SortDialog
from ui.library_panel import LibraryPanel
from ui.detail_panel import DetailPanel
from ui.fetch_dialog import FetchDialog
from ui.batch_dialog import BatchDialog
from ui.rename_dialog import RenameDialog
from ui.settings_dialog import SettingsDialog
from ui.workers import ScanWorker, SaveWorker, FetchWorker, CoverDownloadWorker
from ui.styles import DARK_THEME, PARCHMENT_THEME, THEMES


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = Config()
        set_tool_paths(
            self.config.get("ffprobe_path", ""),
            self.config.get("ffmpeg_path", ""),
        )
        self._books: list[AudioBook] = []
        self._libation_data: dict[str, MetadataResult] = {}
        self._scan_worker = None
        self._active_save_workers: set[SaveWorker] = set()
        self._save_worker_paths: dict[SaveWorker, set[str]] = {}
        self._saving_paths: set[str] = set()

        self.setWindowTitle("AudioBook Manager")
        self.setMinimumSize(1100, 700)

        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        self._connect_signals()

        self._apply_theme()
        self._apply_display_settings()
        self._restore_window_state()

        # Auto-load Libation data if configured
        libation_path = self.config.get("libation_export_path", "")
        if libation_path and os.path.exists(libation_path):
            self._load_libation(libation_path)

        # Auto-scan last folder
        last_folder = self.config.get("last_root_folder", "")
        if last_folder and os.path.isdir(last_folder):
            self._scan_folder(last_folder)

    def _setup_ui(self):
        # Main splitter
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(2)

        self.library_panel = LibraryPanel()
        self.detail_panel = DetailPanel()

        self.splitter.addWidget(self.library_panel)
        self.splitter.addWidget(self.detail_panel)
        self.splitter.setSizes([380, 720])

        self.setCentralWidget(self.splitter)

    def _setup_menu(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        open_action = QAction("&Open Folder...", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self._on_open_folder)
        file_menu.addAction(open_action)

        scan_action = QAction("&Rescan", self)
        scan_action.setShortcut(QKeySequence("F5"))
        scan_action.triggered.connect(self._on_rescan)
        file_menu.addAction(scan_action)

        file_menu.addSeparator()

        import_libation = QAction("Import &Libation Export...", self)
        import_libation.triggered.connect(self._on_import_libation)
        file_menu.addAction(import_libation)

        file_menu.addSeparator()

        settings_action = QAction("&Settings...", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._on_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        save_action = QAction("&Save Current Tags", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self._on_save_current)
        edit_menu.addAction(save_action)

        save_all_action = QAction("Save &All Modified", self)
        save_all_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_all_action.triggered.connect(self._on_save_all_modified)
        edit_menu.addAction(save_all_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        fetch_action = QAction("&Fetch Metadata (Selected)", self)
        fetch_action.setShortcut(QKeySequence("Ctrl+F"))
        fetch_action.triggered.connect(self._on_fetch_selected)
        tools_menu.addAction(fetch_action)

        batch_fetch_action = QAction("Fetch &All Metadata", self)
        batch_fetch_action.triggered.connect(self._on_batch_fetch)
        tools_menu.addAction(batch_fetch_action)

        tools_menu.addSeparator()

        rename_action = QAction("&Rename Folders...", self)
        rename_action.triggered.connect(self._on_rename)
        tools_menu.addAction(rename_action)

        sort_action = QAction("&Sort Library to Disk...", self)
        sort_action.triggered.connect(self._on_sort_library)
        tools_menu.addAction(sort_action)

        tools_menu.addSeparator()

        download_covers_action = QAction("&Download All Covers", self)
        download_covers_action.triggered.connect(self._on_download_covers)
        tools_menu.addAction(download_covers_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        open_btn = QAction("Open Folder", self)
        open_btn.triggered.connect(self._on_open_folder)
        toolbar.addAction(open_btn)

        scan_btn = QAction("Rescan", self)
        scan_btn.triggered.connect(self._on_rescan)
        toolbar.addAction(scan_btn)

        toolbar.addSeparator()

        fetch_btn = QAction("Fetch Selected", self)
        fetch_btn.triggered.connect(self._on_fetch_selected)
        toolbar.addAction(fetch_btn)

        fetch_all_btn = QAction("Fetch All", self)
        fetch_all_btn.triggered.connect(self._on_batch_fetch)
        toolbar.addAction(fetch_all_btn)

        toolbar.addSeparator()

        save_btn = QAction("Save Tags", self)
        save_btn.triggered.connect(self._on_save_current)
        toolbar.addAction(save_btn)

        save_all_btn = QAction("Save All", self)
        save_all_btn.triggered.connect(self._on_save_all_modified)
        toolbar.addAction(save_all_btn)

        toolbar.addSeparator()

        rename_btn = QAction("Rename Folders", self)
        rename_btn.triggered.connect(self._on_rename)
        toolbar.addAction(rename_btn)

        toolbar.addSeparator()

        settings_btn = QAction("Settings", self)
        settings_btn.triggered.connect(self._on_settings)
        toolbar.addAction(settings_btn)

    def _setup_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _connect_signals(self):
        self.library_panel.book_selected.connect(self._on_book_selected)
        self.library_panel.fetch_requested.connect(self._on_context_fetch)
        self.detail_panel.save_requested.connect(self._on_save_book)
        self.detail_panel.fetch_requested.connect(self._on_fetch_single)
        self.detail_panel.revert_requested.connect(self._on_revert_book)

    # --- Actions ---

    def _on_open_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Audio Books Folder",
            self.config.get("last_root_folder", ""),
        )
        if folder and self._scan_folder(folder):
            self.config.set("last_root_folder", folder)
            self.config.save()

    def _on_rescan(self):
        folder = self.config.get("last_root_folder", "")
        if folder and os.path.isdir(folder):
            self._scan_folder(folder)

    def _on_import_libation(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Libation Export", "", "Excel Files (*.xlsx)"
        )
        if path:
            self.config.set("libation_export_path", path)
            self.config.save()
            self._load_libation(path)

    def _on_settings(self):
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            set_tool_paths(
                self.config.get("ffprobe_path", ""),
                self.config.get("ffmpeg_path", ""),
            )
            libation_path = self.config.get("libation_export_path", "")
            if libation_path:
                self._load_libation(libation_path)
            else:
                self._libation_data = {}
            # Apply display settings and theme
            self._apply_theme()
            self._apply_display_settings()

    def _on_book_selected(self, book: AudioBook):
        self.detail_panel.set_book(book)

    def _on_save_current(self):
        books = self.library_panel.get_selected_books()
        if not books:
            return
        self._start_background_save(books)

    def _on_save_book(self, book: AudioBook):
        self._start_background_save([book])

    def _start_background_save(self, books: list[AudioBook]):
        """Save without blocking the UI while Mutagen rewrites large M4B files."""
        worker = self._make_save_worker(books)
        if worker is None:
            return
        worker.finished_signal.connect(self._on_background_save_finished)
        pending = worker.books
        count_label = pending[0].display_title if len(pending) == 1 else f"{len(pending)} audiobooks"
        self.status_bar.showMessage(f"Saving {count_label}...")
        worker.start()

    def _make_save_worker(self, books: list[AudioBook]) -> SaveWorker | None:
        """Claim paths for every save entry point, including batch saves."""
        pending = []
        pending_paths = set()
        for book in books:
            path_key = os.path.normcase(os.path.realpath(os.path.abspath(book.file_path)))
            if path_key not in self._saving_paths:
                pending.append(book)
                pending_paths.add(path_key)
                self._saving_paths.add(path_key)

        if not pending:
            self.status_bar.showMessage("That audiobook is already being saved")
            return None

        worker = SaveWorker(pending, self)
        self._active_save_workers.add(worker)
        self._save_worker_paths[worker] = pending_paths
        worker.book_saved.connect(self._rename_file_if_enabled)
        worker.finished.connect(self._on_background_save_stopped)
        return worker

    def _on_background_save_finished(self, success: int, errors: int):
        self.library_panel.refresh_current()
        if errors:
            QMessageBox.warning(
                self,
                "Save Failed",
                f"Saved {success} audiobook(s); {errors} could not be saved.",
            )
        else:
            self.status_bar.showMessage(f"Saved {success} audiobook(s)")

    def _on_background_save_stopped(self):
        worker = self.sender()
        if not isinstance(worker, SaveWorker):
            return
        self._release_save_paths(worker)
        worker.deleteLater()

    def _release_save_paths(self, worker: SaveWorker):
        self._active_save_workers.discard(worker)
        for path_key in self._save_worker_paths.pop(worker, set()):
            self._saving_paths.discard(path_key)

    def _rename_file_if_enabled(self, book: AudioBook):
        if self.config.get("rename_file_on_save", False):
            template = self.config.get("file_rename_template", "{series}, Book {number} [{identifier}]")
            rename_file(book, template)

    def _on_save_all_modified(self):
        modified = [b for b in self._books if b.is_modified]
        if not modified:
            self.status_bar.showMessage("No modified books to save")
            return

        worker = self._make_save_worker(modified)
        if worker is None:
            return
        dlg = BatchDialog(worker.books, "Save Tags", self)
        dlg.set_worker(worker)
        worker.progress.connect(lambda c, t: dlg.update_progress(c, t))
        worker.finished_signal.connect(lambda s, e: dlg.set_finished(s, e))
        worker.finished_signal.connect(lambda _s, _e: self.library_panel.refresh_current())
        worker.start()
        dlg.exec()

    def _on_revert_book(self, book: AudioBook):
        self.library_panel.refresh_current()

    def _on_fetch_selected(self):
        books = self.library_panel.get_selected_books()
        if not books:
            return
        if len(books) == 1:
            self._on_fetch_single(books[0])
        else:
            self._batch_fetch_books(books)

    def _on_context_fetch(self, books: list[AudioBook]):
        if len(books) == 1:
            self._on_fetch_single(books[0])
        elif books:
            self._batch_fetch_books(books)

    def _on_fetch_single(self, book: AudioBook):
        scrapers = self._get_scrapers()
        try:
            dlg = FetchDialog(book, scrapers, self._libation_data, self)
            dlg.metadata_applied.connect(self._on_metadata_applied)
            dlg.exec()
        except Exception as e:
            QMessageBox.warning(self, "Fetch Error", str(e))

    def _on_metadata_applied(self, book: AudioBook, result: MetadataResult):
        self.detail_panel.apply_metadata_result(book, result)

        # Download cover if available
        if result.cover_url and not book.has_embedded_cover:
            worker = CoverDownloadWorker([(book, result.cover_url)], self)
            worker.finished_signal.connect(
                lambda success, errors, target=book: self._on_single_cover_finished(
                    target, success, errors
                )
            )
            worker.finished.connect(worker.deleteLater)
            worker.start()

        self.library_panel.refresh_current()
        self.status_bar.showMessage(f"Metadata applied for: {book.display_title}")

    def _on_single_cover_finished(self, book: AudioBook, success: int, errors: int):
        if success and self.detail_panel._current_book is book:
            self.detail_panel.cover_widget.set_cover(book.cover_path)
        elif errors:
            self.status_bar.showMessage(f"Cover download failed for: {book.display_title}")

    def _on_batch_fetch(self):
        if not self._books:
            return
        self._batch_fetch_books(self._books)

    def _batch_fetch_books(self, books: list[AudioBook]):
        scrapers = self._get_scrapers()
        dlg = BatchDialog(books, "Fetch Metadata", self)
        worker = FetchWorker(books, scrapers, self)
        dlg.set_worker(worker)

        worker.progress.connect(lambda c, t, title: dlg.update_progress(c, t, title))
        worker.result.connect(self._on_batch_fetch_result)
        worker.error.connect(lambda book, err: dlg.add_log(f"Error ({book.display_title}): {err}"))
        worker.finished_signal.connect(dlg.set_finished)
        worker.finished.connect(worker.deleteLater)

        worker.start()
        dlg.exec()

    def _on_batch_fetch_result(self, book: AudioBook, result: MetadataResult):
        if not any(active is book for active in self._books):
            return
        # Apply non-empty fields
        for field in ("title", "subtitle", "author", "narrator", "series",
                      "series_number", "description", "publisher", "year",
                      "genre", "language"):
            val = getattr(result, field, "")
            if val and not getattr(book, field, ""):
                setattr(book, field, val)
        book.check_modified()
        if self.detail_panel._current_book is book:
            self.detail_panel.refresh_book_state(book, refresh_metadata=True)
        row = next(index for index, active in enumerate(self._books) if active is book)
        self.library_panel.model.refresh_row(row)
        self.library_panel._update_info()

    def _on_rename(self):
        books = self.library_panel.get_selected_books()
        if not books:
            books = self._books
        if not books:
            return

        self._scan_worker = None
        if not self._stop_background_workers():
            self.status_bar.showMessage("A background operation is still stopping; try again shortly")
            return
        QApplication.processEvents()
        if not self._confirm_unsaved_changes("renaming folders", discard_changes=True):
            return
        self.detail_panel._on_stop_preview()
        tracked_paths = [
            (book, Path(book.file_path), Path(book.folder_path)) for book in self._books
        ]
        selected_folders = [(book, Path(book.folder_path)) for book in books]

        dlg = RenameDialog(books, self)
        dlg.renames_completed.connect(
            lambda n: self.status_bar.showMessage(f"Renamed {n} folders")
        )
        if dlg.exec():
            # Naming is driven only by selected books; the entire moved folder
            # also contains unselected tracked siblings and nested folders.
            moves = [
                (source, Path(book.folder_path))
                for book, source in selected_folders
                if str(source) != book.folder_path
            ]
            moves.sort(key=lambda move: len(move[0].parts), reverse=True)
            for book, old_file, old_folder in tracked_paths:
                for source, destination in moves:
                    try:
                        relative_file = old_file.relative_to(source)
                        relative_folder = old_folder.relative_to(source)
                    except ValueError:
                        continue
                    book.file_path = str(destination / relative_file)
                    book.folder_path = str(destination / relative_folder)
                    break
            for row in range(len(self._books)):
                self.library_panel.model.refresh_row(row)
            self.library_panel._update_info()
            current = self.detail_panel._current_book
            if current is not None:
                self.detail_panel.refresh_book_state(current)

    def _on_sort_library(self):
        if not self._books:
            return
        dest = self.config.get("last_root_folder", "D:\\Audio-Books")
        dlg = SortDialog(self._books, dest, self)
        dlg.sort_completed.connect(
            lambda n: self.status_bar.showMessage(f"Sorted {n} files")
        )
        if dlg.exec():
            self._on_rescan()

    def _on_download_covers(self):
        # Collect books that need covers and have a source for them
        books_and_urls = []
        for book in self._books:
            if book.has_embedded_cover:
                continue
            # Try Libation data for cover URL
            if book.identifier in self._libation_data:
                url = self._libation_data[book.identifier].cover_url
                if url:
                    books_and_urls.append((book, url))

        if not books_and_urls:
            self.status_bar.showMessage("No covers to download")
            return

        dlg = BatchDialog([b for b, _ in books_and_urls], "Download Covers", self)
        worker = CoverDownloadWorker(books_and_urls, self)
        dlg.set_worker(worker)
        worker.progress.connect(lambda c, t, title: dlg.update_progress(c, t, title))
        worker.finished_signal.connect(lambda s, e: dlg.set_finished(s, e))
        worker.finished.connect(worker.deleteLater)
        worker.start()
        dlg.exec()

    def _on_about(self):
        QMessageBox.about(
            self, "AudioBook Manager",
            "AudioBook Manager\n\n"
            "A tool for managing audiobook metadata.\n"
            "Supports fetching from Audible, Google Books,\n"
            "OpenLibrary, and Libation exports."
        )

    # --- Helpers ---

    def _apply_theme(self):
        theme_name = self.config.get("theme", "Parchment")
        theme_css = THEMES.get(theme_name, PARCHMENT_THEME)
        self.setStyleSheet(theme_css)

    def _apply_display_settings(self):
        show_num = self.config.get("show_book_number_in_title", True)
        self.library_panel.model.show_book_number_in_title = show_num
        # Refresh table to reflect the change
        self.library_panel.model.layoutChanged.emit()
        self.library_panel._update_info()

    def _scan_folder(self, folder: str) -> bool:
        # Discard a superseded scan's queued results before draining workers.
        self._scan_worker = None
        if not self._stop_background_workers():
            self.status_bar.showMessage("A background operation is still stopping; try again shortly")
            return False
        QApplication.processEvents()
        if not self._confirm_unsaved_changes("reloading the library"):
            return False

        self.status_bar.showMessage(f"Scanning {folder}...")
        self.detail_panel.clear()

        self._scan_worker = ScanWorker(folder, self)
        self._scan_worker.progress.connect(
            lambda c, t: self.status_bar.showMessage(f"Scanning... {c}/{t}")
        )
        worker = self._scan_worker
        worker.finished_signal.connect(
            lambda books, active=worker: self._on_scan_complete(active, books)
        )
        self._scan_worker.start()
        return True

    def _on_scan_complete(self, worker: ScanWorker, books: list[AudioBook]):
        if worker is not self._scan_worker:
            worker.deleteLater()
            return
        self._books = books
        self.library_panel.set_books(books)
        self.status_bar.showMessage(f"Loaded {len(books)} audiobooks")
        self._scan_worker = None
        worker.deleteLater()

    def _load_libation(self, path: str):
        self.status_bar.showMessage("Loading Libation export...")
        self._libation_data = parse_libation_export(path)
        self.status_bar.showMessage(
            f"Loaded {len(self._libation_data)} entries from Libation export"
        )

    def _get_scrapers(self) -> list:
        scrapers = []
        enabled = self.config.get("scrapers_enabled", {})
        delay = self.config.get("scraping_delay", 1.5)

        if enabled.get("audible_api", True):
            scrapers.append(AudibleAPIScraper())
        if enabled.get("audible", True):
            scrapers.append(AudibleScraper(delay=delay))
        if enabled.get("google_books", True):
            scrapers.append(GoogleBooksScraper())
        if enabled.get("openlibrary", True):
            scrapers.append(OpenLibraryScraper())
        if enabled.get("goodreads", True):
            scrapers.append(GoodreadsScraper(delay=delay))

        return scrapers

    def closeEvent(self, event):
        self._scan_worker = None
        if not self._stop_background_workers():
            QMessageBox.warning(
                self, "Background Work Active",
                "A background operation is still stopping. Please close the app again shortly.",
            )
            event.ignore()
            return
        QApplication.processEvents()
        if not self._confirm_unsaved_changes("closing"):
            event.ignore()
            return

        self._persist_window_state()
        self.config.save()
        super().closeEvent(event)

    def _confirm_unsaved_changes(self, action: str, discard_changes: bool = False) -> bool:
        """Preserve unsaved changes before replacing the library or closing."""
        modified = [b for b in self._books if b.is_modified]
        if not modified:
            return True
        reply = QMessageBox.question(
            self, "Unsaved Changes",
            f"You have {len(modified)} book(s) with unsaved changes.\nSave before {action}?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
        )
        if reply == QMessageBox.Save:
            failed_titles = self._save_books_blocking(modified)
            if failed_titles:
                QMessageBox.warning(
                    self, "Save Failed",
                    "These books could not be saved:\n"
                    + "\n".join(failed_titles),
                )
                return False
            if any(book.is_modified for book in self._books):
                self.status_bar.showMessage(f"New edits remain unsaved. Save them before {action}.")
                return False
            return True
        if reply == QMessageBox.Discard:
            if discard_changes:
                # Only metadata participates in the unsaved-tag snapshot.
                # Covers are already persisted; chapter editor drafts stay put.
                for book in modified:
                    book.revert()
                    self.detail_panel.refresh_book_state(book, refresh_metadata=True)
                for row in range(len(self._books)):
                    self.library_panel.model.refresh_row(row)
                self.library_panel._update_info()
            return True
        return False

    def _restore_window_state(self):
        geometry = self.config.get("window_geometry")
        if geometry:
            try:
                self.restoreGeometry(QByteArray(base64.b64decode(geometry.encode("ascii"))))
            except (ValueError, TypeError):
                pass

        splitter_sizes = self.config.get("splitter_sizes")
        if isinstance(splitter_sizes, list) and len(splitter_sizes) == 2:
            self.splitter.setSizes(splitter_sizes)

    def _persist_window_state(self):
        self.config.set(
            "window_geometry",
            base64.b64encode(bytes(self.saveGeometry())).decode("ascii"),
        )
        self.config.set("splitter_sizes", self.splitter.sizes())

    def _save_books_blocking(self, books: list) -> list[str]:
        """Save modified books on a worker thread and block until finished."""
        failed_titles: list[str] = []
        loop = QEventLoop(self)
        worker = self._make_save_worker(books)
        if worker is None:
            return [book.display_title for book in books]
        worker.book_failed.connect(
            lambda book: failed_titles.append(book.display_title)
        )
        worker.finished.connect(loop.quit)
        worker.start()
        loop.exec()
        return failed_titles

    def _stop_background_workers(self) -> bool:
        workers = [worker for worker in self.findChildren(QThread) if worker.isRunning()]
        for worker in workers:
            cancel = getattr(worker, "cancel", None)
            if callable(cancel):
                cancel()
            worker.requestInterruption()
            worker.quit()
        stopped = [worker.wait(16000) for worker in workers]
        return all(stopped)
