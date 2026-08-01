"""Dialog for fetching metadata from multiple sources - parchment theme."""

import os
import random
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QScrollArea, QWidget, QFrame, QCheckBox,
)
from PySide6.QtCore import Qt, Signal, QThread, QSignalBlocker
from PySide6.QtGui import (
    QPixmap, QPalette, QBrush, QPainter, QColor, QPen,
    QPainterPath, QLinearGradient,
)

from core.app_paths import resource_dir
from core.models import AudioBook, MetadataResult

PAPER_PATH = str(resource_dir() / "paper_bg.jpg")

METADATA_FIELDS = [
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


class LeatherButton(QPushButton):
    """Dark embossed leather button."""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(48)
        self.setMinimumWidth(180)
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)
        radius = 10
        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), radius, radius)
        gradient = QLinearGradient(0, rect.top(), 0, rect.bottom())
        gradient.setColorAt(0.0, QColor("#5C3820"))
        gradient.setColorAt(0.3, QColor("#3A2010"))
        gradient.setColorAt(0.7, QColor("#2E1808"))
        gradient.setColorAt(1.0, QColor("#1C0E04"))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawPath(path)
        inner_top = QPainterPath()
        inner_rect = rect.adjusted(2, 2, -2, int(-rect.height() * 0.6))
        inner_top.addRoundedRect(inner_rect.x(), inner_rect.y(), inner_rect.width(), inner_rect.height(), radius - 2, radius - 2)
        painter.setBrush(QColor(255, 255, 255, 20))
        painter.drawPath(inner_top)
        pen = QPen(QColor(10, 5, 2, 200), 1.5)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)
        pen = QPen(QColor(120, 80, 40, 60), 0.5)
        painter.setPen(pen)
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), radius - 2, radius - 2)
        painter.setPen(QColor("#D4A76A"))
        font = self.font()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.text())
        painter.end()


class PaperCell(QWidget):
    """A clickable cell with paper texture background."""
    clicked = Signal()
    _paper_full = None
    _paper_loaded = False

    def __init__(self, selected=False, parent=None):
        super().__init__(parent)
        self.selected = selected
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(44)

        if not PaperCell._paper_loaded and os.path.exists(PAPER_PATH):
            PaperCell._paper_full = QPixmap(PAPER_PATH)
            PaperCell._paper_loaded = True

        if PaperCell._paper_full:
            pw = PaperCell._paper_full.width()
            ph = PaperCell._paper_full.height()
            self._crop_x = random.randint(0, max(0, pw - 200))
            self._crop_y = random.randint(0, max(0, ph - 200))
        else:
            self._crop_x = 0
            self._crop_y = 0

    def paintEvent(self, event):
        from PySide6.QtCore import QRect, QRectF

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        border_w = 4
        rect = QRectF(self.rect()).adjusted(border_w + 2, border_w + 2, -(border_w + 2), -(border_w + 2))
        radius = 10

        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

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

        if not self.selected:
            painter.fillPath(path, QColor(15, 8, 4, 140))

        painter.setClipping(False)

        outer_rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        gradient = QLinearGradient(0, outer_rect.top(), 0, outer_rect.bottom())
        gradient.setColorAt(0.0, QColor("#D4A76A"))
        gradient.setColorAt(0.3, QColor("#8B6538"))
        gradient.setColorAt(0.5, QColor("#DDB880"))
        gradient.setColorAt(0.7, QColor("#7A5528"))
        gradient.setColorAt(1.0, QColor("#6B4520"))

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(gradient))
        border_path = QPainterPath()
        border_path.addRoundedRect(outer_rect, radius + border_w, radius + border_w)
        border_path -= path
        painter.drawPath(border_path)

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


class SingleFetchWorker(QThread):
    result_ready = Signal(str, object)
    error_occurred = Signal(str, str)
    finished_signal = Signal()

    def __init__(self, book, scrapers, libation_data=None, parent=None):
        super().__init__(parent)
        self.book = book
        self.scrapers = scrapers
        self.libation_data = libation_data
        self._cancelled = False

    def run(self):
        if self._cancelled:
            self.finished_signal.emit()
            return
        if self.libation_data and self.book.identifier in self.libation_data:
            result = self.libation_data[self.book.identifier]
            self.result_ready.emit("Libation", result)

        for scraper in self.scrapers:
            if self._cancelled:
                break
            # Skip scrapers that need an ASIN if we don't have one
            if self.book.identifier:
                if not scraper.supports_identifier_type(self.book.identifier_type):
                    continue
            else:
                # No identifier — only try scrapers that can search by title
                if not scraper.supports_identifier_type("unknown"):
                    continue
            try:
                result = scraper.fetch(
                    self.book.identifier,
                    self.book.identifier_type,
                    title_hint=self.book.title,
                    author_hint=self.book.author,
                )
                if result:
                    self.result_ready.emit(scraper.name(), result)
            except Exception as e:
                self.error_occurred.emit(scraper.name(), str(e))

        self.finished_signal.emit()

    def cancel(self):
        self._cancelled = True


class FetchDialog(QDialog):
    metadata_applied = Signal(object, object)

    def __init__(self, book: AudioBook, scrapers: list, libation_data: dict = None, parent=None):
        super().__init__(parent)
        self.book = book
        self.scrapers = scrapers
        self.libation_data = libation_data or {}
        self._results: dict[str, MetadataResult] = {}
        self._source_names: list[str] = []
        self._cells: dict[tuple[str, int], PaperCell] = {}
        self._cell_values: dict[tuple[str, int], str] = {}
        self._selected: dict[str, int] = {}
        self._source_checks: dict[int, QCheckBox] = {}
        self._errors: dict[str, str] = {}
        self._worker = None

        self.setWindowTitle(f"Fetch Metadata - {book.display_title} - Fetching...")
        self.setMinimumSize(1100, 750)

        # Parchment background - use palette so it doesn't fight with child widgets
        self.setStyleSheet("")
        if os.path.exists(PAPER_PATH):
            from PySide6.QtGui import QPixmap, QPalette, QBrush
            palette = self.palette()
            palette.setBrush(QPalette.Window, QBrush(QPixmap(PAPER_PATH)))
            self.setPalette(palette)
            self.setAutoFillBackground(True)

        self._setup_ui()
        self._start_fetch()

    def _setup_ui(self):
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setSpacing(10)
        self._main_layout.setContentsMargins(16, 16, 16, 16)

        # Progress bar (shown during fetch, hidden when done)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #C4B08A; border: none; border-radius: 4px; height: 6px; }
            QProgressBar::chunk { background-color: #6B4520; border-radius: 4px; }
        """)
        self._main_layout.addWidget(self.progress_bar)

        # Scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QWidget { background: transparent; }
            QScrollBar:vertical { background-color: transparent; width: 12px; margin: 4px 2px; }
            QScrollBar::handle:vertical {
                background-color: #8B6538;
                border: 1px solid #6B4520;
                border-radius: 5px;
                min-height: 40px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #D4A76A;
                border-color: #8B6538;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
        """)
        self._main_layout.addWidget(self.scroll)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.cancel_btn = LeatherButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)

        self.apply_btn = LeatherButton("Apply Selected")
        self.apply_btn.clicked.connect(self._on_apply)
        self.apply_btn.setEnabled(False)

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.apply_btn)
        self._main_layout.addLayout(btn_layout)

    def _build_rows(self):
        """Build the field rows after results are in."""
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(4)

        # Header row
        header = QHBoxLayout()
        header.setContentsMargins(4, 0, 4, 0)
        header.setSpacing(8)
        lbl_field = QLabel("FIELD")
        lbl_field.setFixedWidth(110)
        lbl_field.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_field.setStyleSheet("font-weight: 700; color: #1a1a1a; font-size: 12px; padding: 8px; letter-spacing: 1px;")
        header.addWidget(lbl_field)

        # Source headers: Current + each fetched source
        all_sources = ["Current"] + self._source_names
        self._source_checks.clear()
        for src_idx, source_name in enumerate(all_sources):
            check = QCheckBox(source_name.upper())
            check.setCursor(Qt.PointingHandCursor)
            check.setToolTip(f"Select every available value from {source_name}")
            check.setStyleSheet("""
                QCheckBox {
                    color: #1a1a1a;
                    font-size: 12px;
                    font-weight: 700;
                    letter-spacing: 1px;
                    spacing: 8px;
                    padding: 8px;
                }
                QCheckBox::indicator {
                    width: 17px;
                    height: 17px;
                    border: 2px solid #6B4520;
                    border-radius: 4px;
                    background: #E8D9B7;
                }
                QCheckBox::indicator:hover {
                    border-color: #B8860B;
                    background: #F5E8C8;
                }
                QCheckBox::indicator:checked {
                    border-color: #8A5B00;
                    background: #FFD34D;
                }
            """)
            check.toggled.connect(
                lambda checked, si=src_idx: self._on_source_toggled(si, checked)
            )
            self._source_checks[src_idx] = check

            header_widget = QWidget()
            header_layout = QHBoxLayout(header_widget)
            header_layout.setContentsMargins(0, 0, 0, 0)
            header_layout.addStretch()
            header_layout.addWidget(check)
            header_layout.addStretch()
            header.addWidget(header_widget, 1)
        scroll_layout.addLayout(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #4A2E18;")
        scroll_layout.addWidget(sep)

        # Build source data list: current values + each result
        sources_data = []
        # Current
        current_data = {}
        for field_key, _ in METADATA_FIELDS:
            current_data[field_key] = getattr(self.book, field_key, "")
        sources_data.append(("Current", current_data))
        # Fetched results
        for name in self._source_names:
            result = self._results[name]
            src_data = {}
            for field_key, _ in METADATA_FIELDS:
                src_data[field_key] = getattr(result, field_key, "")
            sources_data.append((name, src_data))

        num_sources = len(sources_data)

        # Field rows
        for i, (field_key, field_label) in enumerate(METADATA_FIELDS):
            is_desc = field_key == "description"

            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(4, 4, 4, 4)
            row_layout.setSpacing(8)

            field_lbl = QLabel(field_label)
            field_lbl.setFixedWidth(110)
            field_lbl.setStyleSheet("font-weight: 700; color: #1a1a1a; padding: 8px; font-size: 15px; letter-spacing: 0.5px;")
            field_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
            if is_desc:
                field_lbl.setAlignment(Qt.AlignTop | Qt.AlignRight)
            row_layout.addWidget(field_lbl)

            self._selected[field_key] = 0  # Default to current

            for src_idx, (src_name, src_data) in enumerate(sources_data):
                val = src_data.get(field_key, "")

                cell = PaperCell(selected=(src_idx == 0))
                if is_desc:
                    cell.setMinimumHeight(120)
                cell_layout = QHBoxLayout(cell)
                cell_layout.setContentsMargins(14, 10, 14, 10)
                cell_layout.setSpacing(0)

                self._cells[(field_key, src_idx)] = cell
                self._cell_values[(field_key, src_idx)] = val

                cell.clicked.connect(
                    lambda fk=field_key, si=src_idx: self._select_cell(fk, si)
                )

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
        self.scroll.setWidget(scroll_widget)
        self._sync_source_checks()

    def _select_cell(self, field_key: str, src_idx: int, sync_headers: bool = True):
        self._selected[field_key] = src_idx
        num_sources = 1 + len(self._source_names)
        for si in range(num_sources):
            cell = self._cells.get((field_key, si))
            if cell:
                cell.set_selected(si == src_idx)
        if sync_headers:
            self._sync_source_checks()

    def _on_source_toggled(self, src_idx: int, checked: bool):
        if checked:
            self._select_source(src_idx)
        else:
            # A field must always have a source, so an already-selected column
            # cannot be cleared wholesale. Restore the checkbox's summary state.
            self._sync_source_checks()

    def _select_source(self, src_idx: int):
        """Select every non-empty field supplied by one metadata source."""
        for field_key, _ in METADATA_FIELDS:
            if self._cell_values.get((field_key, src_idx)):
                self._select_cell(field_key, src_idx, sync_headers=False)
        self._sync_source_checks()

    def _sync_source_checks(self):
        """Keep column checkboxes in sync with the per-field selections."""
        for src_idx, check in self._source_checks.items():
            available_fields = [
                field_key for field_key, _ in METADATA_FIELDS
                if self._cell_values.get((field_key, src_idx))
            ]
            all_selected = bool(available_fields) and all(
                self._selected.get(field_key) == src_idx
                for field_key in available_fields
            )
            blocker = QSignalBlocker(check)
            check.setEnabled(bool(available_fields))
            check.setChecked(all_selected)
            del blocker

    def _start_fetch(self):
        self._worker = SingleFetchWorker(
            self.book, self.scrapers, self.libation_data, self.parent() or self
        )
        self._worker.result_ready.connect(self._on_result)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.finished_signal.connect(self._on_finished)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _on_result(self, source_name: str, result: MetadataResult):
        self._results[source_name] = result
        if source_name not in self._source_names:
            self._source_names.append(source_name)

    def _on_error(self, source_name: str, error: str):
        self._errors[source_name] = error

    def _on_finished(self):
        self.progress_bar.hide()
        self.setWindowTitle(
            f"Fetch Metadata - {self.book.display_title} - Found {len(self._results)} source(s)"
        )

        if self._results:
            self._build_rows()
            self.apply_btn.setEnabled(True)
        else:
            # No results - show message
            message = "No metadata sources returned results."
            if self._errors:
                details = "\n".join(f"{name}: {error}" for name, error in self._errors.items())
                message += f"\n\nProvider errors:\n{details}"
            no_results = QLabel(message)
            no_results.setWordWrap(True)
            no_results.setStyleSheet("color: #3B2010; font-size: 15px; font-weight: 600;")
            no_results.setAlignment(Qt.AlignCenter)
            scroll_widget = QWidget()
            layout = QVBoxLayout(scroll_widget)
            layout.addStretch()
            layout.addWidget(no_results)
            layout.addStretch()
            self.scroll.setWidget(scroll_widget)

    def _on_apply(self):
        merged = MetadataResult(source="merged")

        for field_key, _ in METADATA_FIELDS:
            src_idx = self._selected.get(field_key, 0)
            val = self._cell_values.get((field_key, src_idx), "")
            setattr(merged, field_key, val)

        # Get cover_url from best source
        priority = ["Libation", "Audible API", "Audible", "Goodreads", "Google Books", "OpenLibrary"]
        for name in priority:
            if name in self._results and self._results[name].cover_url:
                merged.cover_url = self._results[name].cover_url
                break
        # Fallback: any source with cover
        if not merged.cover_url:
            for result in self._results.values():
                if result.cover_url:
                    merged.cover_url = result.cover_url
                    break

        self.metadata_applied.emit(self.book, merged)
        self.accept()

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
        super().closeEvent(event)

    def reject(self):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
        super().reject()
