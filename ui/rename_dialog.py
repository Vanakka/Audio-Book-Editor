"""Rename preview/confirmation dialog."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit,
)
from PySide6.QtCore import Qt, Signal

from core.models import AudioBook
from core.renamer import preview_renames, execute_renames, TEMPLATES


class RenameDialog(QDialog):
    renames_completed = Signal(int)  # number of successful renames

    def __init__(self, books: list[AudioBook], parent=None):
        super().__init__(parent)
        self.books = books
        self.setWindowTitle(f"Rename Folders - {len(books)} books")
        self.setMinimumSize(700, 500)
        self._setup_ui()
        self._update_preview()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Template selection
        tmpl_layout = QHBoxLayout()
        tmpl_layout.addWidget(QLabel("Template:"))

        self.template_combo = QComboBox()
        for name, _ in TEMPLATES:
            self.template_combo.addItem(name)
        self.template_combo.currentIndexChanged.connect(self._update_preview)
        tmpl_layout.addWidget(self.template_combo, 1)

        # Custom template
        tmpl_layout.addWidget(QLabel("Custom:"))
        self.custom_template = QLineEdit()
        self.custom_template.setPlaceholderText("{series}, Book {number}")
        self.custom_template.textChanged.connect(self._update_preview)
        tmpl_layout.addWidget(self.custom_template, 1)

        layout.addLayout(tmpl_layout)

        # Preview table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Current Name", "->", "New Name"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 30)
        layout.addWidget(self.table)

        # Warning label
        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color: #C62828;")
        layout.addWidget(self.warning_label)

        # Buttons
        btn_layout = QHBoxLayout()
        self.rename_btn = QPushButton("Rename All")
        self.rename_btn.setObjectName("primaryButton")
        self.rename_btn.clicked.connect(self._on_rename)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.rename_btn)
        layout.addLayout(btn_layout)

    def _get_template(self) -> str:
        custom = self.custom_template.text().strip()
        if custom:
            return custom
        idx = self.template_combo.currentIndex()
        if 0 <= idx < len(TEMPLATES):
            return TEMPLATES[idx][1]
        return TEMPLATES[0][1]

    def _update_preview(self):
        template = self._get_template()
        previews = preview_renames(self.books, template)

        self.table.setRowCount(len(previews))
        conflicts = 0

        for row, (book, old_name, new_name, conflict) in enumerate(previews):
            old_item = QTableWidgetItem(old_name)
            old_item.setFlags(Qt.ItemIsEnabled)

            arrow_item = QTableWidgetItem("->")
            arrow_item.setFlags(Qt.ItemIsEnabled)
            arrow_item.setTextAlignment(Qt.AlignCenter)

            new_item = QTableWidgetItem(new_name)
            new_item.setFlags(Qt.ItemIsEnabled)

            if conflict:
                new_item.setForeground(Qt.red)
                conflicts += 1
            elif old_name != new_name:
                new_item.setForeground(Qt.cyan)

            self.table.setItem(row, 0, old_item)
            self.table.setItem(row, 1, arrow_item)
            self.table.setItem(row, 2, new_item)

        if conflicts:
            self.warning_label.setText(f"{conflicts} conflict(s) detected - these will be skipped")
        else:
            self.warning_label.clear()

    def _on_rename(self):
        template = self._get_template()
        success, errors = execute_renames(self.books, template)
        self.renames_completed.emit(success)
        self.accept()
