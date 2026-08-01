"""Details tab for the detail panel."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QPlainTextEdit, QPushButton, QLabel, QScrollArea, QFrame,
    QDialog, QListWidget, QListWidgetItem, QMessageBox,
)

from scrapers.audible_api import search_catalog
from ui.detail.widgets import PaperGroupBox


class DetailsTabMixin:
    def _build_details_tab(self):
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        form = QVBoxLayout(content)
        form.setSpacing(10)
        form.setContentsMargins(12, 12, 12, 12)

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

        extra_group = PaperGroupBox("Additional Information")
        extra_form = QVBoxLayout()
        extra_form.setSpacing(8)
        extra_form.setContentsMargins(12, 8, 12, 8)

        extra_fields = QFormLayout()
        extra_fields.setSpacing(8)
        extra_fields.setLabelAlignment(Qt.AlignRight)

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

        self.genre_edit = QLineEdit()
        self.genre_edit.setPlaceholderText("Genre / Categories")
        extra_fields.addRow(self._label("Genre"), self.genre_edit)

        extra_form.addLayout(extra_fields)
        extra_group.setLayout(extra_form)
        form.addWidget(extra_group)

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