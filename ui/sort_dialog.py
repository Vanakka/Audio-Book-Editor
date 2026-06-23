"""Sort Library to Disk dialog — organize audiobooks into series folders."""

import os
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QLineEdit, QFileDialog, QMessageBox,
    QAbstractItemView, QProgressBar, QStackedWidget, QWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from core.models import AudioBook
from core.renamer import group_by_series, preview_sort, execute_sort
from ui.detail_panel import PaperGroupBox


class SortDialog(QDialog):
    sort_completed = Signal(int)

    def __init__(self, books: list[AudioBook], default_dest: str = "", parent=None):
        super().__init__(parent)
        self.books = books
        self.default_dest = default_dest or "D:\\Audio-Books"
        self._previews = []

        self.setWindowTitle("Sort Library to Disk")
        self.setMinimumSize(950, 700)
        self._setup_ui()
        self._populate_series()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self._build_configure_page()
        self._build_preview_page()
        self.stack.setCurrentIndex(0)

    def _build_configure_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        # Title
        title = QLabel("Sort Library to Disk")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #3B2010;")
        layout.addWidget(title)

        subtitle = QLabel("Organize your audiobooks into series folders automatically")
        subtitle.setStyleSheet("font-size: 12px; color: #6B4520; font-style: italic;")
        layout.addWidget(subtitle)

        # Destination
        dest_group = PaperGroupBox("Destination")

        dest_layout = QHBoxLayout()
        dest_layout.setContentsMargins(12, 8, 12, 8)
        dest_layout.addWidget(QLabel("Root Folder:"))
        self.dest_edit = QLineEdit(self.default_dest)
        dest_layout.addWidget(self.dest_edit, 1)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._on_browse_dest)
        dest_layout.addWidget(browse_btn)
        dest_group.setLayout(dest_layout)
        layout.addWidget(dest_group)

        # Series table
        self.series_group = PaperGroupBox("Series")

        series_layout = QVBoxLayout()
        series_layout.setContentsMargins(12, 8, 12, 8)

        # Bulk actions
        bulk_layout = QHBoxLayout()
        bulk_layout.setSpacing(8)
        set_all_label = QLabel("Set all to:")
        set_all_label.setStyleSheet("font-weight: 600; color: #3B2010;")
        bulk_layout.addWidget(set_all_label)
        for status in ["Ongoing", "Complete", "Skip"]:
            btn = QPushButton(status)
            btn.setFixedHeight(26)
            btn.setStyleSheet("padding: 2px 12px; font-size: 11px;")
            btn.clicked.connect(lambda checked, s=status: self._set_all_series(s))
            bulk_layout.addWidget(btn)
        bulk_layout.addStretch()
        series_layout.addLayout(bulk_layout)

        self.series_table = QTableWidget()
        self.series_table.setColumnCount(4)
        self.series_table.setHorizontalHeaderLabels(["Series Name", "Books", "Current Folder", "Status"])
        self.series_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.series_table.verticalHeader().setVisible(False)
        self.series_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        header = self.series_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        self.series_table.setColumnWidth(3, 110)

        series_layout.addWidget(self.series_table)
        self.series_group.setLayout(series_layout)
        layout.addWidget(self.series_group)

        # Standalone books
        self.standalone_group = PaperGroupBox("Books Without Series")

        standalone_layout = QVBoxLayout()
        standalone_layout.setContentsMargins(12, 8, 12, 8)

        self.standalone_table = QTableWidget()
        self.standalone_table.setColumnCount(4)
        self.standalone_table.setHorizontalHeaderLabels(["Title", "Author", "Genre", "Sort To"])
        self.standalone_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.standalone_table.verticalHeader().setVisible(False)
        self.standalone_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        header2 = self.standalone_table.horizontalHeader()
        header2.setSectionResizeMode(0, QHeaderView.Stretch)
        header2.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header2.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header2.setSectionResizeMode(3, QHeaderView.Interactive)
        self.standalone_table.setColumnWidth(3, 140)

        standalone_layout.addWidget(self.standalone_table)
        self.standalone_group.setLayout(standalone_layout)
        layout.addWidget(self.standalone_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("font-size: 11px; color: #6B4520; font-style: italic;")

        preview_btn = QPushButton("Preview Changes")
        preview_btn.setObjectName("primaryButton")
        preview_btn.clicked.connect(self._on_preview)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.stats_label)
        btn_layout.addStretch()
        btn_layout.addWidget(preview_btn)
        layout.addLayout(btn_layout)

        self.stack.addWidget(page)

    def _build_preview_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        title = QLabel("Preview Changes")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #3B2010;")
        layout.addWidget(title)

        subtitle = QLabel("Files will be moved as shown below")
        subtitle.setStyleSheet("font-size: 12px; color: #6B4520; font-style: italic;")
        layout.addWidget(subtitle)

        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(3)
        self.preview_table.setHorizontalHeaderLabels(["Current Location", "→", "New Location"])
        self.preview_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.preview_table.verticalHeader().setVisible(False)

        header = self.preview_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        layout.addWidget(self.preview_table)

        self.preview_summary = QLabel("")
        self.preview_summary.setStyleSheet("font-size: 13px; font-weight: 600; color: #3B2010;")
        layout.addWidget(self.preview_summary)

        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Buttons
        btn_layout = QHBoxLayout()
        back_btn = QPushButton("Back")
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        self.execute_btn = QPushButton("Execute Sort")
        self.execute_btn.setObjectName("primaryButton")
        self.execute_btn.clicked.connect(self._on_execute)
        btn_layout.addWidget(back_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.execute_btn)
        layout.addLayout(btn_layout)

        self.stack.addWidget(page)

    def _populate_series(self):
        series_map, no_series = group_by_series(self.books)

        # Series table
        self.series_group.setTitle(f"Series ({len(series_map)} found)")
        self.series_table.setRowCount(len(series_map))
        self._series_combos = {}

        for row, (series_name, books) in enumerate(sorted(series_map.items())):
            name_item = QTableWidgetItem(series_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.series_table.setItem(row, 0, name_item)

            count_item = QTableWidgetItem(str(len(books)))
            count_item.setTextAlignment(Qt.AlignCenter)
            count_item.setFlags(count_item.flags() & ~Qt.ItemIsEditable)
            self.series_table.setItem(row, 1, count_item)

            # Show current folder for reference
            current_folder = ""
            if books:
                folder = Path(books[0].folder_path)
                # Show parent if it's a series folder
                if folder.parent.name and folder.parent.name != folder.name:
                    current_folder = folder.parent.name
                else:
                    current_folder = folder.name
            folder_item = QTableWidgetItem(current_folder)
            folder_item.setFlags(folder_item.flags() & ~Qt.ItemIsEditable)
            folder_item.setForeground(QColor("#6B4520"))
            self.series_table.setItem(row, 2, folder_item)

            combo = QComboBox()
            combo.addItems(["Ongoing", "Complete", "Skip"])

            # Guess status from folder name
            if books:
                check_folder = Path(books[0].folder_path).name
                check_parent = Path(books[0].folder_path).parent.name
                check = f"{check_folder} {check_parent}".lower()
                if "complete" in check:
                    combo.setCurrentText("Complete")
                elif "ongoing" in check:
                    combo.setCurrentText("Ongoing")

            self.series_table.setCellWidget(row, 3, combo)
            self._series_combos[series_name] = combo

        # Standalone table
        self._standalone_combos = {}
        self._standalone_books = no_series
        if no_series:
            self.standalone_group.setTitle(f"Books Without Series ({len(no_series)})")
            self.standalone_table.setRowCount(len(no_series))
            self.standalone_table.show()

            for row, book in enumerate(no_series):
                title_item = QTableWidgetItem(book.display_title)
                title_item.setFlags(title_item.flags() & ~Qt.ItemIsEditable)
                self.standalone_table.setItem(row, 0, title_item)

                author_item = QTableWidgetItem(book.author)
                author_item.setFlags(author_item.flags() & ~Qt.ItemIsEditable)
                self.standalone_table.setItem(row, 1, author_item)

                first_genre = ""
                if book.genre:
                    first_genre = book.genre.split(",")[0].strip()
                genre_item = QTableWidgetItem(first_genre or "(none)")
                genre_item.setFlags(genre_item.flags() & ~Qt.ItemIsEditable)
                self.standalone_table.setItem(row, 2, genre_item)

                combo = QComboBox()
                combo.addItem("Skip")
                combo.addItem("Standalone")
                if book.genre:
                    genres = [g.strip() for g in book.genre.split(",") if g.strip()]
                    for g in genres[:4]:
                        combo.addItem(f"Genre: {g}")
                self.standalone_table.setCellWidget(row, 3, combo)
                self._standalone_combos[book.file_path] = combo
        else:
            self.standalone_group.setTitle("Books Without Series")
            self.standalone_table.hide()

        # Stats
        series_books = sum(len(b) for b in series_map.values())
        self.stats_label.setText(f"{series_books} books in series | {len(no_series)} standalone")

    def _set_all_series(self, status: str):
        for combo in self._series_combos.values():
            combo.setCurrentText(status)

    def _on_browse_dest(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder", self.dest_edit.text())
        if folder:
            self.dest_edit.setText(folder)

    def _on_preview(self):
        dest = self.dest_edit.text().strip()
        if not dest or not os.path.isdir(dest):
            QMessageBox.warning(self, "Error", "Please select a valid destination folder.")
            return

        series_config = {}
        for series_name, combo in self._series_combos.items():
            series_config[series_name] = combo.currentText()

        standalone_config = {}
        for file_path, combo in self._standalone_combos.items():
            choice = combo.currentText()
            if choice == "Skip":
                continue
            elif choice == "Standalone":
                standalone_config[file_path] = "Standalone"
            elif choice.startswith("Genre: "):
                standalone_config[file_path] = choice[7:]

        self._previews = preview_sort(self.books, dest, series_config, standalone_config=standalone_config)

        if not self._previews:
            QMessageBox.information(self, "Nothing to Move",
                                    "No files need to be moved. They may already be in the right place, "
                                    "or all series are set to Skip.")
            return

        self.preview_table.setRowCount(len(self._previews))
        conflicts = 0

        for row, (book, old_path, new_path, conflict) in enumerate(self._previews):
            old_item = QTableWidgetItem(old_path)
            old_item.setToolTip(old_path)

            arrow_item = QTableWidgetItem("→")
            arrow_item.setTextAlignment(Qt.AlignCenter)

            new_item = QTableWidgetItem(new_path)
            new_item.setToolTip(new_path)

            if conflict:
                new_item.setForeground(QColor("#C62828"))
                conflicts += 1

            self.preview_table.setItem(row, 0, old_item)
            self.preview_table.setItem(row, 1, arrow_item)
            self.preview_table.setItem(row, 2, new_item)

        movable = len(self._previews) - conflicts
        self.preview_summary.setText(
            f"{len(self._previews)} files to process | {movable} will be moved | {conflicts} conflicts (skipped)"
        )

        self.stack.setCurrentIndex(1)

    def _on_execute(self):
        if not self._previews:
            return

        reply = QMessageBox.question(
            self, "Confirm Sort",
            f"Move {len(self._previews)} files to their new locations?\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.execute_btn.setEnabled(False)
        self.progress_bar.setRange(0, len(self._previews))
        self.progress_bar.show()

        success, errors = execute_sort(self._previews)

        self.progress_bar.setValue(len(self._previews))
        self.preview_summary.setText(f"Done! {success} files moved, {errors} errors.")

        if success > 0:
            self.sort_completed.emit(success)

        QMessageBox.information(
            self, "Sort Complete",
            f"Moved {success} files successfully.\n{errors} errors."
        )
        self.accept()
