"""Cover art display widget."""

from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Signal


class CoverWidget(QWidget):
    cover_changed = Signal(str)
    cover_removed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cover_path = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.setFixedSize(250, 250)
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(250, 250)
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setStyleSheet(
            "QLabel { background-color: palette(midlight); border-radius: 8px; border: 1px solid palette(mid); }"
        )
        self._show_placeholder()
        layout.addWidget(self.cover_label, alignment=Qt.AlignCenter)

    def set_cover(self, path: str | None):
        self._cover_path = path
        if path and Path(path).exists():
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                # Scale to fit inside the label, preserving aspect ratio
                label_size = self.cover_label.size()
                scaled = pixmap.scaled(
                    label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.cover_label.setPixmap(scaled)
                return
        self._show_placeholder()

    def _show_placeholder(self):
        self.cover_label.setText("No Cover")
        self.cover_label.setPixmap(QPixmap())
