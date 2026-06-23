"""Mockup of Fetch Metadata dialog - leather + paper theme."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QWidget, QFrame, QPushButton, QProgressBar,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QPalette, QBrush, QPainter, QColor, QPen

# Texture paths
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
LEATHER_PATH = os.path.join(RES, "leather_bg_1080.jpg")
PAPER_PATH = os.path.join(RES, "paper_bg.jpg")

# Sample data
CURRENT = {
    "title": "The Healer's Way",
    "subtitle": "",
    "author": "Oleg Sapphire, Alexey Kovtunov, Jennifer E. Sunseri - translator",
    "narrator": "Jonathan Johns",
    "series": "Healer's Way",
    "series_number": "13",
    "description": "I was the most powerful healer in my world — the best, having devoted my entire life to mastering the healing arts...",
    "publisher": "Tantor Media",
    "year": "2026",
    "genre": "",
    "language": "English",
}

AUDIBLE = {
    "title": "The Healer's Way",
    "subtitle": "The Healer's Way, Book 13",
    "author": "Oleg Sapphire, Alexey Kovtunov",
    "narrator": "Jonathan Johns",
    "series": "Healer's Way",
    "series_number": "13",
    "description": "Mikhail's power had only grown with every new day, and his Family was also flourishing. However, something dark lurks beneath the surface of their world...",
    "publisher": "Tantor Media",
    "year": "2025",
    "genre": "Literature & Fiction, Action & Adventure, Fantasy",
    "language": "english",
}

GOODREADS = {
    "title": "The Healer's Way #13",
    "subtitle": "",
    "author": "Oleg Sapphire",
    "narrator": "",
    "series": "The Healer's Way",
    "series_number": "13",
    "description": "I was the most powerful healer in my world — the best, having devoted my entire life to mastering the healing arts. But fate had other plans...",
    "publisher": "",
    "year": "2025",
    "genre": "Fantasy, Magic, Urban Fantasy, Science Fiction",
    "language": "",
}

FIELDS = [
    ("title", "Title"),
    ("subtitle", "Subtitle"),
    ("author", "Author"),
    ("narrator", "Narrator"),
    ("series", "Series"),
    ("series_number", "Book #"),
    ("description", "Description"),
    ("publisher", "Publisher"),
    ("year", "Year"),
    ("genre", "Genre"),
    ("language", "Language"),
]


class PaperCell(QWidget):
    """A clickable cell with paper texture background painted via QPainter."""
    clicked = Signal()

    _paper_full = None  # Full-size paper image for random cropping
    _paper_loaded = False

    def __init__(self, selected=False, parent=None):
        super().__init__(parent)
        self.selected = selected
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(44)
        self._crop_offset = None  # Random crop position

        if not PaperCell._paper_loaded and os.path.exists(PAPER_PATH):
            PaperCell._paper_full = QPixmap(PAPER_PATH)
            PaperCell._paper_loaded = True

        # Pick a random crop offset
        import random
        if PaperCell._paper_full:
            pw = PaperCell._paper_full.width()
            ph = PaperCell._paper_full.height()
            self._crop_x = random.randint(0, max(0, pw - 200))
            self._crop_y = random.randint(0, max(0, ph - 200))
        else:
            self._crop_x = 0
            self._crop_y = 0

    def paintEvent(self, event):
        from PySide6.QtGui import QPainterPath, QLinearGradient
        from PySide6.QtCore import QRect, QRectF

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        border_w = 4
        rect = QRectF(self.rect()).adjusted(border_w + 2, border_w + 2, -(border_w + 2), -(border_w + 2))
        radius = 10

        # Build rounded path
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        # Draw paper texture into rounded shape
        painter.setClipPath(path)
        if PaperCell._paper_full:
            pw = PaperCell._paper_full.width()
            ph = PaperCell._paper_full.height()
            crop_w = min(int(rect.width()) + 100, pw - self._crop_x)
            crop_h = min(int(rect.height()) + 100, ph - self._crop_y)
            source_rect = QRect(self._crop_x, self._crop_y, crop_w, crop_h)
            cropped = PaperCell._paper_full.copy(source_rect)
            scaled = cropped.scaled(int(rect.width()), int(rect.height()), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(int(rect.x()), int(rect.y()), scaled)
        else:
            painter.fillPath(path, QColor("#D4C4A0"))

        # Dim unselected
        if not self.selected:
            painter.fillPath(path, QColor(80, 50, 30, 100))

        painter.setClipping(False)

        # Border
        outer_rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        outer_path = QPainterPath()
        outer_path.addRoundedRect(outer_rect, radius + border_w, radius + border_w)

        # Bronze gradient border
        gradient = QLinearGradient(0, outer_rect.top(), 0, outer_rect.bottom())
        gradient.setColorAt(0.0, QColor("#D4A76A"))
        gradient.setColorAt(0.3, QColor("#8B6538"))
        gradient.setColorAt(0.5, QColor("#DDB880"))
        gradient.setColorAt(0.7, QColor("#7A5528"))
        gradient.setColorAt(1.0, QColor("#6B4520"))

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(gradient))
        # Draw border as difference between outer and inner path
        border_path = QPainterPath()
        border_path.addRoundedRect(outer_rect, radius + border_w, radius + border_w)
        border_path -= path
        painter.drawPath(border_path)

        # Selected: gold border on top
        if self.selected:
            gold_gradient = QLinearGradient(0, outer_rect.top(), 0, outer_rect.bottom())
            gold_gradient.setColorAt(0.0, QColor("#FFD700"))
            gold_gradient.setColorAt(0.3, QColor("#DAA520"))
            gold_gradient.setColorAt(0.5, QColor("#FFE44D"))
            gold_gradient.setColorAt(0.7, QColor("#DAA520"))
            gold_gradient.setColorAt(1.0, QColor("#B8860B"))
            painter.setBrush(QBrush(gold_gradient))
            painter.setPen(Qt.NoPen)
            painter.drawPath(border_path)
        painter.end()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def set_selected(self, selected: bool):
        self.selected = selected
        self.update()


class MockupFetchDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fetch Metadata - The Healer's Way (Book 13)")
        self.setMinimumSize(1100, 750)
        self._cells = {}
        self._selected = {}

        # Solid dark background
        self.setStyleSheet("QDialog { background-color: #D2B48C; }")

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Status
        status = QLabel("Done. Found data from 2 source(s). Click a cell to select it, then click Apply.")
        status.setStyleSheet("color: #5C3310; font-size: 13px; font-weight: 500; background: transparent;")
        layout.addWidget(status)

        progress = QProgressBar()
        progress.setRange(0, 1)
        progress.setValue(1)
        progress.setStyleSheet("""
            QProgressBar { background-color: #C4A882; border: none; border-radius: 4px; height: 6px; }
            QProgressBar::chunk { background-color: #8B5A3C; border-radius: 4px; }
        """)
        layout.addWidget(progress)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QWidget { background: transparent; }
            QScrollBar:vertical { background-color: #C4A882; width: 8px; border-radius: 4px; }
            QScrollBar::handle:vertical { background-color: #8B6B4A; min-height: 30px; border-radius: 4px; }
            QScrollBar::handle:vertical:hover { background-color: #6B4520; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(4)

        # Header row
        header = QHBoxLayout()
        header.setSpacing(8)
        lbl_field = QLabel("FIELD")
        lbl_field.setFixedWidth(90)
        lbl_field.setStyleSheet("font-weight: 700; color: #5C3310; font-size: 12px; padding: 6px; letter-spacing: 1px;")
        header.addWidget(lbl_field)

        for source_name in ["CURRENT", "AUDIBLE API", "GOODREADS"]:
            lbl = QLabel(source_name)
            lbl.setStyleSheet("font-weight: 700; color: #5C3310; font-size: 12px; padding: 6px; letter-spacing: 1px;")
            header.addWidget(lbl, 1)
        scroll_layout.addLayout(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #8B5A3C;")
        scroll_layout.addWidget(sep)

        # Field rows
        sources = [("Current", CURRENT), ("Audible API", AUDIBLE), ("Goodreads", GOODREADS)]

        for i, (field_key, field_label) in enumerate(FIELDS):
            is_desc = field_key == "description"

            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(4, 4, 4, 4)
            row_layout.setSpacing(8)

            field_lbl = QLabel(field_label)
            field_lbl.setFixedWidth(110)
            field_lbl.setStyleSheet("font-weight: 700; color: #5C3310; padding: 8px; font-size: 15px; letter-spacing: 0.5px;")
            field_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
            if is_desc:
                field_lbl.setAlignment(Qt.AlignTop | Qt.AlignRight)
            row_layout.addWidget(field_lbl)

            self._selected[field_key] = 0

            for src_idx, (src_name, src_data) in enumerate(sources):
                val = src_data.get(field_key, "")

                cell = PaperCell(selected=(src_idx == 0))
                if is_desc:
                    cell.setMinimumHeight(120)
                cell_layout = QHBoxLayout(cell)
                cell_layout.setContentsMargins(14, 10, 14, 10)
                cell_layout.setSpacing(0)

                self._cells[(field_key, src_idx)] = cell
                cell.clicked.connect(lambda fk=field_key, si=src_idx: self._select_cell(fk, si))

                val_lbl = QLabel(val if val else "(empty)")
                val_lbl.setWordWrap(True)
                if is_desc:
                    val_lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
                if val:
                    val_lbl.setStyleSheet("color: #3B2010; font-size: 13px; font-weight: 600; background: transparent;")
                else:
                    val_lbl.setStyleSheet("color: #9B8B7B; font-size: 13px; font-style: italic; background: transparent;")
                cell_layout.addWidget(val_lbl, 1)

                row_layout.addWidget(cell, 1)

            scroll_layout.addLayout(row_layout)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        apply_btn = QPushButton("Apply Selected")
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #6B4520; color: #F5E6D0; font-weight: 600;
                padding: 10px 24px; border-radius: 6px; border: none; font-size: 13px;
            }
            QPushButton:hover { background-color: #8B5A3C; }
        """)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #C4A882; color: #3B2010;
                padding: 10px 24px; border-radius: 6px; border: 1px solid #8B6B4A; font-size: 13px;
            }
            QPushButton:hover { background-color: #B8986A; }
        """)

        btn_layout.addWidget(apply_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _select_cell(self, field_key: str, src_idx: int):
        self._selected[field_key] = src_idx
        for si in range(3):
            cell = self._cells.get((field_key, si))
            if cell:
                cell.set_selected(si == src_idx)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dlg = MockupFetchDialog()
    dlg.show()
    sys.exit(app.exec())
