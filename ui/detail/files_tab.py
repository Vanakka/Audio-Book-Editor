"""Files tab for the detail panel."""

import re
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QMessageBox, QCheckBox,
)

from core.renamer import rename_to_filename
from ui.detail.widgets import PaperGroupBox


class FilesTabMixin:
    def _build_files_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        layout.addWidget(self._label("Current Filename"))
        self.current_filename_label = QLabel("")
        self.current_filename_label.setWordWrap(True)
        self.current_filename_label.setStyleSheet("font-size: 13px; font-weight: 600; padding: 8px;")
        layout.addWidget(self.current_filename_label)

        self.include_series_cb = QCheckBox("Include series name in filename")
        self.include_series_cb.setChecked(False)
        self.include_series_cb.toggled.connect(self._on_include_series_toggled)
        layout.addWidget(self.include_series_cb)

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

        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #8B6538;")
        layout.addWidget(sep)

        layout.addWidget(self._label("File Information"))
        self.file_info_label = QLabel("")
        self.file_info_label.setStyleSheet("font-size: 12px; padding: 8px;")
        self.file_info_label.setWordWrap(True)
        self.file_info_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.file_info_label)

        open_folder_btn = QPushButton("Open Folder in Explorer")
        open_folder_btn.clicked.connect(self._on_open_folder)
        layout.addWidget(open_folder_btn)

        layout.addStretch()
        self.tabs.addTab(widget, "Files")

    def _build_suggested_filename(self, book):
        if not book.title or not book.series_number:
            return book.filename

        clean_title = re.sub(
            r'[,:_\-\s]*\s*Book\s*\d+(?:\.\d+)?\s*$', '', book.title, flags=re.IGNORECASE
        ).strip()
        clean_title = re.sub(
            r'\s*\(Book\s*\d+(?:\.\d+)?\)\s*$', '', clean_title, flags=re.IGNORECASE
        ).strip()
        clean_title = re.sub(r'\s*#\d+(?:\.\d+)?\s*$', '', clean_title).strip()
        clean_title = re.sub(r'[<>:"/\\|?*]', '', clean_title)

        if self.include_series_cb.isChecked() and book.series:
            clean_series = re.sub(r'[<>:"/\\|?*]', '', book.series)
            return f"{clean_series}, {clean_title} (Book {book.series_number}).m4b"
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