"""Batch operations dialog with progress tracking."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QCheckBox, QGroupBox,
)
from PySide6.QtCore import Qt, Signal

from core.models import AudioBook


class BatchDialog(QDialog):
    def __init__(self, books: list[AudioBook], operation: str, parent=None):
        super().__init__(parent)
        self.books = books
        self.operation = operation
        self._worker = None

        self.setWindowTitle(f"Batch {operation} - {len(books)} books")
        self.setMinimumSize(500, 400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Info
        self.info_label = QLabel(f"Processing {len(self.books)} books...")
        self.info_label.setObjectName("sectionHeader")
        layout.addWidget(self.info_label)

        # Current item
        self.current_label = QLabel("")
        layout.addWidget(self.current_label)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(self.books))
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(200)
        layout.addWidget(self.log)

        # Results
        self.results_label = QLabel("")
        layout.addWidget(self.results_label)

        # Buttons
        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._on_cancel)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setEnabled(False)

        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

    def set_worker(self, worker):
        self._worker = worker

    def update_progress(self, current: int, total: int, label: str = ""):
        self.progress_bar.setValue(current)
        if label:
            self.current_label.setText(f"Processing: {label}")

    def add_log(self, message: str):
        self.log.append(message)

    def set_finished(self, success: int, errors: int):
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.current_label.setText("Done!")
        self.results_label.setText(
            f"Completed: {success} successful, {errors} errors"
        )
        self.results_label.setStyleSheet(
            "color: #2E7D32;" if errors == 0 else "color: #B8860B;"
        )
        self.cancel_btn.setEnabled(False)
        self.close_btn.setEnabled(True)
        self._worker = None

    def _on_cancel(self):
        if self._worker:
            self._worker.cancel()
        self.reject()

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(2000)
        super().closeEvent(event)
