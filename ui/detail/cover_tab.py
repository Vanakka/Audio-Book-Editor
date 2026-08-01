"""Cover tab for the detail panel."""

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QMessageBox, QComboBox,
)

from core.models import AudioBook
from scrapers.cover_search import search_audible_covers, search_goodreads_covers
from ui.cover_widget import CoverWidget
from ui.detail.widgets import PaperGroupBox, download_and_embed_cover, embed_cover_file


class CoverTabMixin:
    def _build_cover_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        cover_group = PaperGroupBox("Current Cover")
        cover_group_layout = QHBoxLayout()
        cover_group_layout.setSpacing(16)

        self.cover_widget = CoverWidget()
        cover_group_layout.addWidget(self.cover_widget, 0, Qt.AlignTop)

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

        search_group = PaperGroupBox("Search Cover Art")
        search_group_layout = QVBoxLayout()
        search_group_layout.setSpacing(10)

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

        self.cover_results_container = QWidget()
        results_container_layout = QVBoxLayout(self.cover_results_container)
        results_container_layout.setContentsMargins(0, 0, 0, 0)
        results_container_layout.setSpacing(4)

        self.cover_results_list = QListWidget()
        self.cover_results_list.setMinimumHeight(200)
        self.cover_results_list.setIconSize(QSize(80, 80))
        self.cover_results_list.itemDoubleClicked.connect(self._on_cover_result_selected)
        results_container_layout.addWidget(self.cover_results_list)

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

    def _on_cover_upload(self):
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(
            self, "Select Cover Image", "",
            "Images (*.jpg *.jpeg *.png *.bmp *.webp)"
        )
        if path and self._current_book:
            book = self._current_book
            self._run_background(
                embed_cover_file, book, path,
                on_result=lambda cover_path, target=book: self._cover_embed_finished(target, cover_path),
                on_error=lambda error: QMessageBox.warning(self, "Cover Error", error),
            )

    def _on_cover_url_download(self):
        url = self.cover_url_edit.text().strip()
        if not url or not self._current_book:
            return
        book = self._current_book
        self._run_background(
            download_and_embed_cover, book, url,
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