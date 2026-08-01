"""Shared widgets and helpers for the detail panel."""

import os
import random
from pathlib import Path

from PySide6.QtCore import Qt, QRect, QRectF
from PySide6.QtGui import QPixmap, QPainter, QColor, QPainterPath, QLinearGradient, QBrush, QPen
from PySide6.QtWidgets import QGroupBox

from core.app_paths import resource_dir
from core.models import AudioBook
from core.metadata import write_cover
from scrapers.cover_downloader import download_cover

PAPER_PATH = str(resource_dir() / "paper_bg.jpg")


def embed_cover_file(book: AudioBook, path: str) -> str:
    with open(path, "rb") as handle:
        data = handle.read()
    preferred = "png" if path.lower().endswith(".png") else "jpeg"
    if not write_cover(book, data, preferred):
        raise ValueError("The selected file is not a valid cover image")
    return book.cover_path or ""


def download_and_embed_cover(book: AudioBook, url: str) -> str:
    path = download_cover(
        url, book.identifier, source_key=book.file_path, force=True
    )
    if not path:
        raise ValueError("The URL did not return a valid image")
    return embed_cover_file(book, path)


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
        self._paper_cache = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        rect = QRectF(self.rect()).adjusted(1, 10, -1, -1)
        radius = 8
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        painter.setClipPath(path)
        if PaperGroupBox._paper_full:
            if self._paper_cache is None or self._paper_cache.size() != self.size():
                pw = PaperGroupBox._paper_full.width()
                ph = PaperGroupBox._paper_full.height()
                crop_w = min(int(rect.width()) + 100, pw - self._crop_x)
                crop_h = min(int(rect.height()) + 100, ph - self._crop_y)
                source_rect = QRect(self._crop_x, self._crop_y, crop_w, crop_h)
                cropped = PaperGroupBox._paper_full.copy(source_rect)
                self._paper_cache = cropped.scaled(
                    int(rect.width()), int(rect.height()),
                    Qt.IgnoreAspectRatio, Qt.SmoothTransformation,
                )
            painter.drawPixmap(int(rect.x()), int(rect.y()), self._paper_cache)
        else:
            painter.fillPath(path, QColor("#D4C4A0"))
        painter.setClipping(False)

        painter.setPen(QPen(QColor("#8B6538"), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)

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
            painter.fillRect(tx, ty, tw, th, QColor("#D4C4A0"))
            painter.setPen(QColor("#6B4520"))
            painter.drawText(tx, ty + fm.ascent(), title_text)

        painter.end()