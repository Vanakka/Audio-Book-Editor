"""Right panel: tabbed metadata editor with Details, Cover, Files, Chapters tabs."""

import os
import re
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QPlainTextEdit, QPushButton, QLabel, QScrollArea, QFrame,
    QDialog, QListWidget, QListWidgetItem, QMessageBox,
    QTabWidget, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QAbstractItemView, QGroupBox, QCheckBox,
)
from PySide6.QtCore import Qt, Signal, QSize, QRect, QRectF, QUrl
from PySide6.QtGui import QPixmap, QPainter, QColor, QPainterPath, QLinearGradient, QBrush, QPen

from core.models import AudioBook
from core.chapters import probe_chapters, rewrite_chapters
from core.metadata import write_cover
from core.renamer import rename_to_filename
from scrapers.cover_downloader import download_cover
from scrapers.cover_search import search_audible_covers, search_goodreads_covers
from scrapers.audible_api import search_catalog
from ui.cover_widget import CoverWidget
from ui.workers import FunctionWorker

import random

RES = Path(__file__).parent.parent / "resources"
PAPER_PATH = str(RES / "paper_bg.jpg")


def _embed_cover_file(book: AudioBook, path: str) -> str:
    with open(path, "rb") as handle:
        data = handle.read()
    preferred = "png" if path.lower().endswith(".png") else "jpeg"
    if not write_cover(book, data, preferred):
        raise ValueError("The selected file is not a valid cover image")
    return book.cover_path or ""


def _download_and_embed_cover(book: AudioBook, url: str) -> str:
    path = download_cover(
        url, book.identifier, source_key=book.file_path, force=True
    )
    if not path:
        raise ValueError("The URL did not return a valid image")
    return _embed_cover_file(book, path)


class PaperGroupBox(QGroupBox):
    """A QGroupBox with random paper texture background and bronze border."""
    _paper_full = None
    _paper_loaded = False

    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        if not PaperGroupBox._paper_loaded and os.path.exists(PAPER_PATH):
            PaperGroupBox._paper_full = QPixmap(PAPER_PATH)
            PaperGroupBox._paper_loaded = True

        if PaperGroupBox._paper_full:
            pw = PaperGroupBox._paper_full.width()
            ph = PaperGroupBox._paper_full.height()
            # Use different quadrants to ensure visible difference from background
            self._crop_x = random.randint(pw // 4, max(pw // 4, pw - 200))
            self._crop_y = random.randint(ph // 4, max(ph // 4, ph - 200))
        else:
            self._crop_x = 0
            self._crop_y = 0

        self.setStyleSheet("""
            QGroupBox {
                background: transparent;
                border: none;
                margin-top: 10px;
                padding: 6px 8px 6px 8px;
            }
        """)
        self._paper_cache = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._paper_cache = None  # Invalidate cache on resize

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        rect = QRectF(self.rect()).adjusted(1, 10, -1, -1)
        radius = 8
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        # 1. Fill paper texture clipped to rounded rect
        painter.setClipPath(path)
        if PaperGroupBox._paper_full:
            if self._paper_cache is None or self._paper_cache.size() != self.size():
                pw = PaperGroupBox._paper_full.width()
                ph = PaperGroupBox._paper_full.height()
                crop_w = min(int(rect.width()) + 100, pw - self._crop_x)
                crop_h = min(int(rect.height()) + 100, ph - self._crop_y)
                source_rect = QRect(self._crop_x, self._crop_y, crop_w, crop_h)
                cropped = PaperGroupBox._paper_full.copy(source_rect)
                self._paper_cache = cropped.scaled(int(rect.width()), int(rect.height()), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(int(rect.x()), int(rect.y()), self._paper_cache)
        else:
            painter.fillPath(path, QColor("#D4C4A0"))
        painter.setClipping(False)

        # 2. Draw border
        painter.setPen(QPen(QColor("#8B6538"), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)

        # 3. Draw title
        if self.title():
            font = painter.font()
            font.setBold(True)
            font.setPointSize(10)
            painter.setFont(font)
            title_text = f"  {self.title()}  "
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(title_text)
            th = fm.height()
            tx = int(rect.x()) + 12
            ty = int(rect.y()) - th // 2
            # Clear area behind title
            painter.fillRect(tx, ty, tw, th, QColor("#D4C4A0"))
            painter.setPen(QColor("#6B4520"))
            painter.drawText(tx, ty + fm.ascent(), title_text)

        painter.end()


class DetailPanel(QWidget):
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

        # Tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Build each tab
        self._build_details_tab()
        self._build_cover_tab()
        self._build_files_tab()
        self._build_chapters_tab()

        # Action buttons (always visible below tabs)
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

        # Connect field changes
        for field in self._all_fields():
            if isinstance(field, QLineEdit):
                field.textChanged.connect(self._on_field_changed)
            elif isinstance(field, QPlainTextEdit):
                field.textChanged.connect(self._on_field_changed)

        self.set_enabled(False)

    # ===================== DETAILS TAB =====================

    def _build_details_tab(self):
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        form = QVBoxLayout(content)
        form.setSpacing(10)
        form.setContentsMargins(12, 12, 12, 12)

        # --- Book Information group ---
        info_group = PaperGroupBox("Book Information")
        info_form = QFormLayout()
        info_form.setSpacing(8)
        info_form.setLabelAlignment(Qt.AlignRight)
        info_form.setContentsMargins(12, 8, 12, 8)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Book title")
        info_form.addRow(self._label("Title"), self.title_edit)

        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("Author name")
        info_form.addRow(self._label("Author"), self.author_edit)

        self.narrator_edit = QLineEdit()
        self.narrator_edit.setPlaceholderText("Narrator name")
        info_form.addRow(self._label("Narrator"), self.narrator_edit)

        self.series_edit = QLineEdit()
        self.series_edit.setPlaceholderText("Series name")
        info_form.addRow(self._label("Series"), self.series_edit)

        self.series_num_edit = QLineEdit()
        self.series_num_edit.setPlaceholderText("#")
        self.series_num_edit.setMaximumWidth(80)
        info_form.addRow(self._label("Book #"), self.series_num_edit)

        self.subtitle_edit = QLineEdit()
        self.subtitle_edit.setPlaceholderText("Subtitle")
        info_form.addRow(self._label("Subtitle"), self.subtitle_edit)

        self.publisher_edit = QLineEdit()
        self.publisher_edit.setPlaceholderText("Publisher")
        info_form.addRow(self._label("Publisher"), self.publisher_edit)

        info_group.setLayout(info_form)
        form.addWidget(info_group)

        # --- Additional Information group ---
        extra_group = PaperGroupBox("Additional Information")
        extra_form = QVBoxLayout()
        extra_form.setSpacing(8)
        extra_form.setContentsMargins(12, 8, 12, 8)

        extra_fields = QFormLayout()
        extra_fields.setSpacing(8)
        extra_fields.setLabelAlignment(Qt.AlignRight)

        # Year + Language on one line
        year_lang_row = QHBoxLayout()
        year_lang_row.setSpacing(8)
        self.year_edit = QLineEdit()
        self.year_edit.setPlaceholderText("Year")
        self.year_edit.setMaximumWidth(100)
        year_lang_row.addWidget(self.year_edit)
        year_lang_row.addWidget(self._label("Language"))
        self.language_edit = QLineEdit()
        self.language_edit.setPlaceholderText("Language")
        self.language_edit.setMaximumWidth(150)
        year_lang_row.addWidget(self.language_edit)
        year_lang_row.addStretch()
        extra_fields.addRow(self._label("Year"), year_lang_row)

        # ASIN + Search + CDEK on one line
        asin_row = QHBoxLayout()
        asin_row.setSpacing(8)
        self.asin_edit = QLineEdit()
        self.asin_edit.setPlaceholderText("e.g. B0D3FKJK7V")
        self.asin_edit.setMaximumWidth(150)
        asin_row.addWidget(self.asin_edit)
        self.asin_search_btn = QPushButton("Search")
        self.asin_search_btn.setFixedHeight(28)
        self.asin_search_btn.setMinimumWidth(70)
        self.asin_search_btn.clicked.connect(self._on_asin_search)
        asin_row.addWidget(self.asin_search_btn)
        asin_row.addWidget(self._label("CDEK"))
        self.cdek_edit = QLineEdit()
        self.cdek_edit.setPlaceholderText("e.g. B0D3FKJK7V")
        self.cdek_edit.setMaximumWidth(150)
        asin_row.addWidget(self.cdek_edit)
        asin_row.addStretch()
        extra_fields.addRow(self._label("ASIN"), asin_row)

        # Genre
        self.genre_edit = QLineEdit()
        self.genre_edit.setPlaceholderText("Genre / Categories")
        extra_fields.addRow(self._label("Genre"), self.genre_edit)

        extra_form.addLayout(extra_fields)
        extra_group.setLayout(extra_form)
        form.addWidget(extra_group)

        # --- Description group ---
        desc_group = PaperGroupBox("Description")
        desc_layout = QVBoxLayout()
        desc_layout.setContentsMargins(12, 8, 12, 8)
        self.description_edit = QPlainTextEdit()
        self.description_edit.setPlaceholderText("Book description...")
        self.description_edit.setMinimumHeight(120)
        desc_layout.addWidget(self.description_edit)
        desc_group.setLayout(desc_layout)
        form.addWidget(desc_group)

        form.addStretch()
        scroll.setWidget(content)

        tab_layout = QVBoxLayout(widget)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        self.tabs.addTab(widget, "Details")

    # ===================== COVER TAB =====================

    def _build_cover_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # === Current Cover group ===
        cover_group = PaperGroupBox("Current Cover")
        cover_group_layout = QHBoxLayout()
        cover_group_layout.setSpacing(16)

        self.cover_widget = CoverWidget()
        cover_group_layout.addWidget(self.cover_widget, 0, Qt.AlignTop)

        # Actions to the right
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(10)
        actions_layout.setAlignment(Qt.AlignTop)

        self.cover_info_label = QLabel("No cover loaded")
        self.cover_info_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        actions_layout.addWidget(self.cover_info_label)

        upload_btn = QPushButton("Upload from File")
        upload_btn.clicked.connect(self._on_cover_upload)
        actions_layout.addWidget(upload_btn)

        url_layout = QHBoxLayout()
        url_layout.setSpacing(8)
        self.cover_url_edit = QLineEdit()
        self.cover_url_edit.setPlaceholderText("Paste image URL here...")
        url_layout.addWidget(self.cover_url_edit, 1)
        url_submit_btn = QPushButton("Download")
        url_submit_btn.setObjectName("primaryButton")
        url_submit_btn.clicked.connect(self._on_cover_url_download)
        url_layout.addWidget(url_submit_btn)
        actions_layout.addLayout(url_layout)

        actions_layout.addStretch()
        cover_group_layout.addLayout(actions_layout, 1)
        cover_group.setLayout(cover_group_layout)
        layout.addWidget(cover_group)

        # === Search Cover Art group ===
        search_group = PaperGroupBox("Search Cover Art")
        search_group_layout = QVBoxLayout()
        search_group_layout.setSpacing(10)

        # Search fields
        search_fields = QHBoxLayout()
        search_fields.setSpacing(8)

        search_fields.addWidget(QLabel("Provider:"))
        self.cover_provider_combo = QComboBox()
        self.cover_provider_combo.addItems(["Audible", "Goodreads"])
        self.cover_provider_combo.setMinimumWidth(120)
        search_fields.addWidget(self.cover_provider_combo)

        search_fields.addWidget(QLabel("Title or ASIN:"))
        self.cover_search_edit = QLineEdit()
        search_fields.addWidget(self.cover_search_edit, 1)

        search_fields.addWidget(QLabel("Author:"))
        self.cover_author_edit = QLineEdit()
        search_fields.addWidget(self.cover_author_edit, 1)

        self.cover_search_btn = QPushButton("Search")
        self.cover_search_btn.setObjectName("primaryButton")
        self.cover_search_btn.clicked.connect(self._on_cover_search)
        search_fields.addWidget(self.cover_search_btn)

        search_group_layout.addLayout(search_fields)

        # Results container (hidden until search)
        self.cover_results_container = QWidget()
        results_container_layout = QVBoxLayout(self.cover_results_container)
        results_container_layout.setContentsMargins(0, 0, 0, 0)
        results_container_layout.setSpacing(4)

        self.cover_results_list = QListWidget()
        self.cover_results_list.setMinimumHeight(200)
        self.cover_results_list.setIconSize(QSize(80, 80))
        self.cover_results_list.itemDoubleClicked.connect(self._on_cover_result_selected)
        results_container_layout.addWidget(self.cover_results_list)

        # Hint + Close button row
        hint_row = QHBoxLayout()
        self.cover_hint_label = QLabel("Double-click a result to download and embed the cover art")
        self.cover_hint_label.setStyleSheet("font-size: 11px; font-style: italic;")
        hint_row.addWidget(self.cover_hint_label)
        hint_row.addStretch()
        self.cover_results_close_btn = QPushButton("Close Results")
        self.cover_results_close_btn.setFixedHeight(28)
        self.cover_results_close_btn.setStyleSheet("""
            QPushButton { background-color: #8B3A2A; color: #F5E6D0; font-weight: 600;
                          font-size: 12px; border: none; border-radius: 4px; padding: 4px 12px; }
            QPushButton:hover { background-color: #A04030; }
        """)
        self.cover_results_close_btn.clicked.connect(self._on_cover_results_close)
        hint_row.addWidget(self.cover_results_close_btn)
        results_container_layout.addLayout(hint_row)

        self.cover_results_container.hide()
        search_group_layout.addWidget(self.cover_results_container)

        search_group.setLayout(search_group_layout)
        layout.addWidget(search_group)

        layout.addStretch()
        self.tabs.addTab(widget, "Cover")

    # ===================== FILES TAB =====================

    def _build_files_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # Current filename
        layout.addWidget(self._label("Current Filename"))
        self.current_filename_label = QLabel("")
        self.current_filename_label.setWordWrap(True)
        self.current_filename_label.setStyleSheet("font-size: 13px; font-weight: 600; padding: 8px;")
        layout.addWidget(self.current_filename_label)

        # Include series toggle
        self.include_series_cb = QCheckBox("Include series name in filename")
        self.include_series_cb.setChecked(False)
        self.include_series_cb.toggled.connect(self._on_include_series_toggled)
        layout.addWidget(self.include_series_cb)

        # Rename
        layout.addWidget(self._label("Rename To"))
        rename_layout = QHBoxLayout()
        self.filename_edit = QLineEdit()
        self.filename_edit.setPlaceholderText("New filename")
        rename_layout.addWidget(self.filename_edit, 1)
        self.rename_btn = QPushButton("Rename")
        self.rename_btn.setFixedHeight(28)
        self.rename_btn.clicked.connect(self._on_rename_file)
        rename_layout.addWidget(self.rename_btn)
        layout.addLayout(rename_layout)

        # Separator
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #8B6538;")
        layout.addWidget(sep)

        # File info
        layout.addWidget(self._label("File Information"))
        self.file_info_label = QLabel("")
        self.file_info_label.setStyleSheet("font-size: 12px; padding: 8px;")
        self.file_info_label.setWordWrap(True)
        self.file_info_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.file_info_label)

        # Open folder button
        open_folder_btn = QPushButton("Open Folder in Explorer")
        open_folder_btn.clicked.connect(self._on_open_folder)
        layout.addWidget(open_folder_btn)

        layout.addStretch()
        self.tabs.addTab(widget, "Files")

    # ===================== CHAPTERS TAB =====================

    def _build_chapters_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        layout.addWidget(self._label("Embedded Chapters"))

        self.chapters_table = QTableWidget()
        self.chapters_table.setColumnCount(3)
        self.chapters_table.setHorizontalHeaderLabels(["#", "Time", "Title"])
        self.chapters_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.chapters_table.verticalHeader().setVisible(False)

        header = self.chapters_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        layout.addWidget(self.chapters_table)

        # Chapter info
        self.chapter_info_label = QLabel("")
        self.chapter_info_label.setStyleSheet("font-size: 11px; color: palette(dark);")
        layout.addWidget(self.chapter_info_label)

        # Preview + Save buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.preview_chapter_btn = QPushButton("Preview (7s)")
        self.preview_chapter_btn.clicked.connect(self._on_preview_chapter)
        btn_row.addWidget(self.preview_chapter_btn)

        self.stop_preview_btn = QPushButton("Stop")
        self.stop_preview_btn.clicked.connect(self._on_stop_preview)
        self.stop_preview_btn.setEnabled(False)
        btn_row.addWidget(self.stop_preview_btn)

        btn_row.addStretch()

        self.save_chapters_btn = QPushButton("Save Chapter Names")
        self.save_chapters_btn.setObjectName("primaryButton")
        self.save_chapters_btn.clicked.connect(self._on_save_chapters)
        btn_row.addWidget(self.save_chapters_btn)

        layout.addLayout(btn_row)

        # Audio player for previews
        from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
        from PySide6.QtCore import QUrl, QTimer

        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(0.5)

        self._preview_timer = QTimer()
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._on_stop_preview)
        self._pending_seek_ms = 0

        # Stop playback when switching tabs
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.tabs.addTab(widget, "Chapters")

    # ===================== HELPERS =====================

    def _run_background(self, function, *args, on_result=None, on_error=None,
                        button: QPushButton | None = None, **kwargs):
        """Run one operation without blocking the UI and retain its worker safely."""
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
            self.genre_edit, self.language_edit,
        ]

    def set_enabled(self, enabled: bool):
        for field in self._all_fields():
            field.setEnabled(enabled)
        self.save_btn.setEnabled(enabled)
        self.fetch_btn.setEnabled(enabled)
        self.revert_btn.setEnabled(enabled)

    # ===================== SET / CLEAR BOOK =====================

    def set_book(self, book: AudioBook):
        # Stop any playing preview when switching books
        self._on_stop_preview()
        self._updating = True
        self._current_book = book

        # Details tab
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

        # Cover tab
        self.cover_widget.set_cover(book.cover_path)
        if book.cover_path and os.path.exists(book.cover_path):
            px = QPixmap(book.cover_path)
            self.cover_info_label.setText(f"{px.width()}x{px.height()}px")
        else:
            self.cover_info_label.setText("No cover loaded")
        self.cover_search_edit.setText(book.title)
        self.cover_author_edit.setText(book.author.split(",")[0].strip() if book.author else "")

        # Files tab
        self.current_filename_label.setText(book.filename)
        self.filename_edit.setText(self._build_suggested_filename(book))

        self.file_info_label.setText(
            f"Path: {book.file_path}\n"
            f"Folder: {book.folder_path}\n"
            f"ID: {book.identifier} ({book.identifier_type})\n"
            f"Source: {book.metadata_source}"
        )

        # Chapters tab
        self._load_chapters(book)

        self.set_enabled(True)
        self._updating = False

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

    # ===================== SYNC =====================

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

    # ===================== DETAILS ACTIONS =====================

    def _on_asin_search(self):
        if not self._current_book:
            return
        title = self.title_edit.text().strip()
        author = self.author_edit.text().strip()
        if not title:
            QMessageBox.information(self, "Search", "Enter a title first.")
            return

        self._run_background(
            search_catalog, title, author,
            on_result=self._show_asin_results,
            on_error=lambda error: QMessageBox.warning(self, "Search Failed", error),
            button=self.asin_search_btn,
        )

    def _show_asin_results(self, products):
        if not self._current_book:
            return

        if not products:
            QMessageBox.information(self, "Search", "No results found on Audible.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Audible Search - {len(products)} results")
        dlg.setMinimumSize(500, 350)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("Select a result to use its ASIN:"))

        listbox = QListWidget()
        for p in products:
            asin = p.get("asin", "?")
            ptitle = p.get("title", "?")
            subtitle = p.get("subtitle", "")
            authors = ", ".join(a.get("name", "") for a in p.get("authors", []))
            series_info = ""
            for s in p.get("series", []):
                series_info = f" [{s.get('title', '')} #{s.get('sequence', '')}]"
            display = f"{ptitle}"
            if subtitle:
                display += f": {subtitle}"
            display += f" - {authors}{series_info} ({asin})"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, asin)
            listbox.addItem(item)
        layout.addWidget(listbox)

        btn_layout = QHBoxLayout()
        select_btn = QPushButton("Use Selected")
        cancel_btn = QPushButton("Cancel")
        select_btn.clicked.connect(dlg.accept)
        cancel_btn.clicked.connect(dlg.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(select_btn)
        layout.addLayout(btn_layout)
        listbox.itemDoubleClicked.connect(lambda: dlg.accept())

        if dlg.exec() == QDialog.Accepted:
            selected = listbox.currentItem()
            if selected:
                asin = selected.data(Qt.UserRole)
                self.asin_edit.setText(asin)
                self.asin_edit.setReadOnly(False)
                self.asin_edit.setStyleSheet("")
                self.cdek_edit.setText(asin)
                self.cdek_edit.setReadOnly(False)
                self.cdek_edit.setStyleSheet("")
                if self._current_book:
                    self._current_book.asin_tag = asin
                    self._current_book.cdek_tag = asin
                    self._current_book.identifier = asin
                    self._current_book.identifier_type = "asin"
                    self._current_book.check_modified()

    # ===================== COVER ACTIONS =====================

    def _on_cover_upload(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Cover Image", "",
            "Images (*.jpg *.jpeg *.png *.bmp *.webp)"
        )
        if path and self._current_book:
            book = self._current_book
            self._run_background(
                _embed_cover_file, book, path,
                on_result=lambda cover_path, target=book: self._cover_embed_finished(target, cover_path),
                on_error=lambda error: QMessageBox.warning(self, "Cover Error", error),
            )

    def _on_cover_url_download(self):
        url = self.cover_url_edit.text().strip()
        if not url or not self._current_book:
            return
        book = self._current_book
        self._run_background(
            _download_and_embed_cover, book, url,
            on_result=lambda cover_path, target=book: self._cover_embed_finished(target, cover_path),
            on_error=lambda error: QMessageBox.warning(self, "Download Failed", error),
        )

    def _on_cover_results_close(self):
        self.cover_results_container.hide()
        self.cover_results_list.clear()

    def _on_cover_search(self):
        query = self.cover_search_edit.text().strip()
        author = self.cover_author_edit.text().strip()
        provider = self.cover_provider_combo.currentText()

        if not query:
            return

        self.cover_results_list.clear()
        self.cover_results_container.show()

        search_function = search_audible_covers if provider == "Audible" else search_goodreads_covers
        self._run_background(
            search_function, query, author,
            on_result=self._show_cover_results,
            on_error=self._show_cover_search_error,
            button=self.cover_search_btn,
        )

    def _show_cover_results(self, results):
        for result in results:
            suffix = f" ({result['asin']})" if result.get("asin") else ""
            item = QListWidgetItem(f"{result.get('title', 'Unknown title')}{suffix}")
            item.setData(Qt.UserRole, result.get("cover_url", ""))
            self.cover_results_list.addItem(item)
        if not results:
            self.cover_results_list.addItem("No covers found")

    def _show_cover_search_error(self, error: str):
        self.cover_results_list.addItem(f"Provider error: {error}")

    def _on_cover_result_selected(self, item: QListWidgetItem):
        url = item.data(Qt.UserRole)
        if not url or not self._current_book:
            return
        self.cover_url_edit.setText(url)
        self._on_cover_url_download()

    def _cover_embed_finished(self, book: AudioBook, cover_path: str):
        if self._current_book is not book:
            return
        self.cover_widget.set_cover(cover_path)
        pixmap = QPixmap(cover_path)
        self.cover_info_label.setText(f"{pixmap.width()}x{pixmap.height()}px")

    # ===================== FILES ACTIONS =====================

    def _build_suggested_filename(self, book):
        """Build a suggested filename based on title, series, and book number."""
        if not book.title or not book.series_number:
            return book.filename

        clean_title = re.sub(r'[,:_\-\s]*\s*Book\s*\d+(?:\.\d+)?\s*$', '', book.title, flags=re.IGNORECASE).strip()
        clean_title = re.sub(r'\s*\(Book\s*\d+(?:\.\d+)?\)\s*$', '', clean_title, flags=re.IGNORECASE).strip()
        clean_title = re.sub(r'\s*#\d+(?:\.\d+)?\s*$', '', clean_title).strip()
        clean_title = re.sub(r'[<>:"/\\|?*]', '', clean_title)

        if self.include_series_cb.isChecked() and book.series:
            clean_series = re.sub(r'[<>:"/\\|?*]', '', book.series)
            return f"{clean_series}, {clean_title} (Book {book.series_number}).m4b"
        else:
            return f"{clean_title} (Book {book.series_number}).m4b"

    def _on_include_series_toggled(self, checked):
        if self._current_book:
            self.filename_edit.setText(self._build_suggested_filename(self._current_book))

    def _on_rename_file(self):
        if not self._current_book:
            return
        book = self._current_book
        new_name = self.filename_edit.text().strip()
        if not new_name:
            return
        if not new_name.lower().endswith(".m4b"):
            new_name += ".m4b"

        old_path = Path(book.file_path)
        if old_path.name == new_name:
            return

        if rename_to_filename(book, new_name):
            self.current_filename_label.setText(new_name)
            self.filename_edit.setText(new_name)
        else:
            QMessageBox.warning(self, "Rename Failed", "The filename is invalid or already exists.")

    def _on_open_folder(self):
        if self._current_book:
            subprocess.Popen(["explorer", self._current_book.folder_path])

    # ===================== CHAPTERS =====================

    def _load_chapters(self, book: AudioBook):
        self.chapters_table.setRowCount(0)
        self._chapters = []
        self.chapter_info_label.setText("Loading chapters...")
        self._run_background(
            probe_chapters, book.file_path,
            on_result=lambda chapters, target=book: self._populate_chapters(target, chapters),
            on_error=lambda error, target=book: self._chapter_load_failed(target, error),
        )

    def _populate_chapters(self, book: AudioBook, chapters: list[dict]):
        if self._current_book is not book:
            return
        self._chapters = chapters
        self.chapters_table.setRowCount(len(chapters))
        for i, chapter in enumerate(chapters):
            title = chapter.get("tags", {}).get("title", f"Chapter {i + 1}")
            start = float(chapter.get("start_time", 0))
            hours = int(start // 3600)
            mins = int((start % 3600) // 60)
            secs = int(start % 60)
            time_str = f"{hours}:{mins:02d}:{secs:02d}" if hours else f"{mins}:{secs:02d}"

            num_item = QTableWidgetItem(str(i + 1))
            num_item.setTextAlignment(Qt.AlignCenter)
            num_item.setFlags(num_item.flags() & ~Qt.ItemIsEditable)
            self.chapters_table.setItem(i, 0, num_item)

            time_item = QTableWidgetItem(time_str)
            time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable)
            self.chapters_table.setItem(i, 1, time_item)
            self.chapters_table.setItem(i, 2, QTableWidgetItem(title))

        total = float(chapters[-1].get("end_time", 0)) if chapters else 0
        self.chapter_info_label.setText(
            f"{len(chapters)} chapters | Total: {int(total // 3600)}h {int((total % 3600) // 60)}m"
        )

    def _chapter_load_failed(self, book: AudioBook, error: str):
        if self._current_book is book:
            self.chapter_info_label.setText(error)

    def _on_preview_chapter(self):
        """Play 7 seconds from the selected chapter's start time."""
        if not self._current_book:
            return
        selected = self.chapters_table.selectedItems()
        if not selected:
            QMessageBox.information(self, "Preview", "Select a chapter first.")
            return

        row = selected[0].row()

        if row >= len(self._chapters):
            return
        ms = int(float(self._chapters[row].get("start_time", 0)) * 1000)

        # Stop any current playback and release file
        self._player.stop()
        self._player.setSource(QUrl())

        # Set new source
        self._player.setSource(QUrl.fromLocalFile(self._current_book.file_path))
        self._pending_seek_ms = ms

        # Disconnect any old connections
        try:
            self._player.mediaStatusChanged.disconnect(self._on_media_ready)
        except RuntimeError:
            pass
        self._player.mediaStatusChanged.connect(self._on_media_ready)

    def _on_media_ready(self, status):
        from PySide6.QtMultimedia import QMediaPlayer
        if status in (QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia):
            try:
                self._player.mediaStatusChanged.disconnect(self._on_media_ready)
            except RuntimeError:
                pass
            self._player.setPosition(self._pending_seek_ms)
            self._player.play()
            self._preview_timer.start(7000)
            self.stop_preview_btn.setEnabled(True)
            self.preview_chapter_btn.setEnabled(False)

    def _on_stop_preview(self):
        """Stop the preview playback."""
        self._player.stop()
        self._player.setSource(QUrl())
        self._preview_timer.stop()
        self.stop_preview_btn.setEnabled(False)
        self.preview_chapter_btn.setEnabled(True)

    def _on_tab_changed(self, index):
        """Stop playback when switching away from Chapters tab."""
        self._on_stop_preview()

    def _on_save_chapters(self):
        """Save edited chapter names back to the M4B file."""
        if not self._current_book:
            return

        # Release the file if player has it open
        self._player.stop()
        self._player.setSource(QUrl())
        self._preview_timer.stop()
        self.stop_preview_btn.setEnabled(False)
        self.preview_chapter_btn.setEnabled(True)

        book = self._current_book
        row_count = self.chapters_table.rowCount()
        if row_count == 0:
            return

        if len(self._chapters) != row_count:
            QMessageBox.warning(self, "Error", "Chapter count mismatch.")
            return

        titles = []
        for i in range(row_count):
            title_item = self.chapters_table.item(i, 2)
            titles.append(title_item.text() if title_item else f"Chapter {i + 1}")
        self._run_background(
            rewrite_chapters, book.file_path, list(self._chapters), titles,
            on_result=lambda _result, target=book: self._chapter_save_finished(target),
            on_error=lambda error: QMessageBox.warning(self, "Chapter Save Failed", error),
            button=self.save_chapters_btn,
        )

    def _chapter_save_finished(self, book: AudioBook):
        if self._current_book is not book:
            return
        QMessageBox.information(self, "Success", "Chapter names saved.")
        self._load_chapters(book)

    # ===================== STANDARD ACTIONS =====================

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
