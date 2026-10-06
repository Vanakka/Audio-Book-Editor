"""Right panel: tabbed metadata editor with Details, Cover, Files, Chapters tabs."""

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPlainTextEdit,
    QPushButton, QLabel, QMessageBox, QTabWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap

from core.models import AudioBook
from ui.workers import FunctionWorker
from ui.detail.details_tab import DetailsTabMixin
from ui.detail.cover_tab import CoverTabMixin
from ui.detail.files_tab import FilesTabMixin
from ui.detail.chapters_tab import ChaptersTabMixin


class DetailPanel(
    QWidget,
    DetailsTabMixin,
    CoverTabMixin,
    FilesTabMixin,
    ChaptersTabMixin,
):
    save_requested = Signal(object)
    fetch_requested = Signal(object)
    revert_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_book: AudioBook | None = None
        self._updating = False
        self._background_workers: set[FunctionWorker] = set()
        self._chapters: list[dict] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 8, 8)
        layout.setSpacing(8)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._build_details_tab()
        self._build_cover_tab()
        self._build_files_tab()
        self._build_chapters_tab()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.fetch_btn = QPushButton("Fetch Metadata")
        self.fetch_btn.setObjectName("primaryButton")
        self.fetch_btn.clicked.connect(self._on_fetch)

        self.save_btn = QPushButton("Save Tags")
        self.save_btn.clicked.connect(self._on_save)

        self.revert_btn = QPushButton("Undo Changes")
        self.revert_btn.clicked.connect(self._on_revert)

        btn_layout.addWidget(self.fetch_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.revert_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        for field in self._all_fields():
            if isinstance(field, QLineEdit):
                field.textChanged.connect(self._on_field_changed)
            elif isinstance(field, QPlainTextEdit):
                field.textChanged.connect(self._on_field_changed)

        self.set_enabled(False)

    def _run_background(self, function, *args, on_result=None, on_error=None,
                        button: QPushButton | None = None, **kwargs):
        worker = FunctionWorker(function, *args, parent=self, **kwargs)
        self._background_workers.add(worker)
        if button:
            button.setEnabled(False)

        if on_result:
            worker.result_ready.connect(on_result)

        def handle_error(message):
            if on_error:
                on_error(message)
            else:
                QMessageBox.warning(self, "Operation Failed", message)

        worker.error_occurred.connect(handle_error)

        def cleanup():
            if button:
                button.setEnabled(True)
            self._background_workers.discard(worker)
            worker.deleteLater()

        worker.finished.connect(cleanup)
        worker.start()
        return worker

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("fieldLabel")
        return lbl

    def _all_fields(self):
        return [
            self.title_edit, self.subtitle_edit, self.author_edit,
            self.narrator_edit, self.series_edit, self.series_num_edit,
            self.description_edit, self.publisher_edit, self.year_edit,
            self.genre_edit, self.language_edit, self.asin_edit, self.cdek_edit,
        ]

    def set_enabled(self, enabled: bool):
        for field in self._all_fields():
            field.setEnabled(enabled)
        self.save_btn.setEnabled(enabled)
        self.fetch_btn.setEnabled(enabled)
        self.revert_btn.setEnabled(enabled)

    def set_book(self, book: AudioBook):
        self._on_stop_preview()
        self._updating = True
        self._current_book = book

        self._refresh_metadata_fields(book)

        self.cover_widget.set_cover(book.cover_path)
        if book.cover_path and os.path.exists(book.cover_path):
            px = QPixmap(book.cover_path)
            self.cover_info_label.setText(f"{px.width()}x{px.height()}px")
        else:
            self.cover_info_label.setText("No cover loaded")
        self.cover_search_edit.setText(book.title)
        self.cover_author_edit.setText(book.author.split(",")[0].strip() if book.author else "")

        self._refresh_file_info(book)
        self.filename_edit.setText(self._build_suggested_filename(book))

        self._load_chapters(book)
        self.set_enabled(True)
        self._updating = False

    def _refresh_metadata_fields(self, book: AudioBook):
        self.title_edit.setText(book.title)
        self.subtitle_edit.setText(book.subtitle)
        self.author_edit.setText(book.author)
        self.narrator_edit.setText(book.narrator)
        self.series_edit.setText(book.series)
        self.series_num_edit.setText(book.series_number)
        self.description_edit.setPlainText(book.description)
        self.publisher_edit.setText(book.publisher)
        self.year_edit.setText(book.year)
        self.genre_edit.setText(book.genre)
        self.language_edit.setText(book.language)

        self.asin_edit.setText(book.asin_tag)
        self.asin_edit.setReadOnly(bool(book.asin_tag))
        self.asin_edit.setStyleSheet("" if not book.asin_tag else "background-color: palette(midlight);")
        self.cdek_edit.setText(book.cdek_tag)
        self.cdek_edit.setReadOnly(bool(book.cdek_tag))
        self.cdek_edit.setStyleSheet("" if not book.cdek_tag else "background-color: palette(midlight);")

    def _refresh_file_info(self, book: AudioBook):
        self.current_filename_label.setText(book.filename)
        self.file_info_label.setText(
            f"Path: {book.file_path}\n"
            f"Folder: {book.folder_path}\n"
            f"ID: {book.identifier} ({book.identifier_type})\n"
            f"Source: {book.metadata_source}"
        )

    def refresh_book_state(self, book: AudioBook, refresh_metadata: bool = False):
        """Refresh tags/paths without replacing cover or chapter editor drafts."""
        if self._current_book is not book:
            return
        was_updating = self._updating
        self._updating = True
        try:
            if refresh_metadata:
                self._refresh_metadata_fields(book)
            self._refresh_file_info(book)
        finally:
            self._updating = was_updating

    def clear(self):
        self._updating = True
        self._current_book = None
        for field in self._all_fields():
            if isinstance(field, QLineEdit):
                field.clear()
            elif isinstance(field, QPlainTextEdit):
                field.clear()
        self.cover_widget.set_cover(None)
        self.cover_info_label.setText("No cover loaded")
        self.current_filename_label.clear()
        self.filename_edit.clear()
        self.asin_edit.clear()
        self.asin_edit.setReadOnly(False)
        self.asin_edit.setStyleSheet("")
        self.cdek_edit.clear()
        self.cdek_edit.setReadOnly(False)
        self.cdek_edit.setStyleSheet("")
        self.file_info_label.clear()
        self.chapters_table.setRowCount(0)
        self._chapters = []
        self.chapter_info_label.clear()
        self.set_enabled(False)
        self._updating = False

    def _sync_to_book(self):
        if not self._current_book:
            return
        book = self._current_book
        book.title = self.title_edit.text().strip()
        book.subtitle = self.subtitle_edit.text().strip()
        book.author = self.author_edit.text().strip()
        book.narrator = self.narrator_edit.text().strip()
        book.series = self.series_edit.text().strip()
        book.series_number = self.series_num_edit.text().strip()
        book.description = self.description_edit.toPlainText().strip()
        book.publisher = self.publisher_edit.text().strip()
        book.year = self.year_edit.text().strip()
        book.genre = self.genre_edit.text().strip()
        book.language = self.language_edit.text().strip()
        if not self.asin_edit.isReadOnly():
            book.asin_tag = self.asin_edit.text().strip()
        if not self.cdek_edit.isReadOnly():
            book.cdek_tag = self.cdek_edit.text().strip()
        book.check_modified()

    def _on_field_changed(self):
        if self._updating:
            return
        self._sync_to_book()

    def _on_fetch(self):
        if self._current_book:
            self.fetch_requested.emit(self._current_book)

    def _on_save(self):
        if self._current_book:
            self._sync_to_book()
            self.save_requested.emit(self._current_book)

    def _on_revert(self):
        if self._current_book:
            self._current_book.revert()
            self.set_book(self._current_book)
            self.revert_requested.emit(self._current_book)

    def apply_metadata_result(self, book: AudioBook, result):
        field_map = {
            "title": "title", "subtitle": "subtitle", "author": "author",
            "narrator": "narrator", "series": "series", "series_number": "series_number",
            "description": "description", "publisher": "publisher",
            "year": "year", "genre": "genre", "language": "language",
        }
        for result_field, book_field in field_map.items():
            val = getattr(result, result_field, "")
            if val:
                setattr(book, book_field, val)
        book.check_modified()
        if self._current_book is book:
            self.set_book(book)
