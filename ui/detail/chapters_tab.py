"""Chapters tab for the detail panel."""

from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox,
)

from core.models import AudioBook
from core.chapters import probe_chapters, rewrite_chapters


class ChaptersTabMixin:
    def _build_chapters_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        layout.addWidget(self._label("Embedded Chapters"))

        self.chapters_table = QTableWidget()
        self.chapters_table.setColumnCount(3)
        self.chapters_table.setHorizontalHeaderLabels(["#", "Time", "Title"])
        self.chapters_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.chapters_table.verticalHeader().setVisible(False)

        header = self.chapters_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        layout.addWidget(self.chapters_table)

        self.chapter_info_label = QLabel("")
        self.chapter_info_label.setStyleSheet("font-size: 11px; color: palette(dark);")
        layout.addWidget(self.chapter_info_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.preview_chapter_btn = QPushButton("Preview (7s)")
        self.preview_chapter_btn.clicked.connect(self._on_preview_chapter)
        btn_row.addWidget(self.preview_chapter_btn)

        self.stop_preview_btn = QPushButton("Stop")
        self.stop_preview_btn.clicked.connect(self._on_stop_preview)
        self.stop_preview_btn.setEnabled(False)
        btn_row.addWidget(self.stop_preview_btn)

        btn_row.addStretch()

        self.save_chapters_btn = QPushButton("Save Chapter Names")
        self.save_chapters_btn.setObjectName("primaryButton")
        self.save_chapters_btn.clicked.connect(self._on_save_chapters)
        btn_row.addWidget(self.save_chapters_btn)

        layout.addLayout(btn_row)

        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(0.5)

        self._preview_timer = QTimer()
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._on_stop_preview)
        self._pending_seek_ms = 0

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.tabs.addTab(widget, "Chapters")

    def _load_chapters(self, book: AudioBook):
        self.chapters_table.setRowCount(0)
        self._chapters = []
        self.chapter_info_label.setText("Loading chapters...")
        self._run_background(
            probe_chapters, book.file_path,
            on_result=lambda chapters, target=book: self._populate_chapters(target, chapters),
            on_error=lambda error, target=book: self._chapter_load_failed(target, error),
        )

    def _populate_chapters(self, book: AudioBook, chapters: list[dict]):
        if self._current_book is not book:
            return
        self._chapters = chapters
        self.chapters_table.setRowCount(len(chapters))
        for i, chapter in enumerate(chapters):
            title = chapter.get("tags", {}).get("title", f"Chapter {i + 1}")
            start = float(chapter.get("start_time", 0))
            hours = int(start // 3600)
            mins = int((start % 3600) // 60)
            secs = int(start % 60)
            time_str = f"{hours}:{mins:02d}:{secs:02d}" if hours else f"{mins}:{secs:02d}"

            num_item = QTableWidgetItem(str(i + 1))
            num_item.setTextAlignment(Qt.AlignCenter)
            num_item.setFlags(num_item.flags() & ~Qt.ItemIsEditable)
            self.chapters_table.setItem(i, 0, num_item)

            time_item = QTableWidgetItem(time_str)
            time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable)
            self.chapters_table.setItem(i, 1, time_item)
            self.chapters_table.setItem(i, 2, QTableWidgetItem(title))

        if not chapters:
            self.chapter_info_label.setText(
                "No embedded chapters found in this file."
            )
            return

        total = float(chapters[-1].get("end_time", 0))
        self.chapter_info_label.setText(
            f"{len(chapters)} chapters | Total: {int(total // 3600)}h {int((total % 3600) // 60)}m"
        )

    def _chapter_load_failed(self, book: AudioBook, error: str):
        if self._current_book is book:
            self.chapter_info_label.setText(error)

    def _on_preview_chapter(self):
        if not self._current_book:
            return
        selected = self.chapters_table.selectedItems()
        if not selected:
            QMessageBox.information(self, "Preview", "Select a chapter first.")
            return

        row = selected[0].row()
        if row >= len(self._chapters):
            return
        ms = int(float(self._chapters[row].get("start_time", 0)) * 1000)

        self._player.stop()
        self._player.setSource(QUrl())
        self._player.setSource(QUrl.fromLocalFile(self._current_book.file_path))
        self._pending_seek_ms = ms

        try:
            self._player.mediaStatusChanged.disconnect(self._on_media_ready)
        except RuntimeError:
            pass
        self._player.mediaStatusChanged.connect(self._on_media_ready)

    def _on_media_ready(self, status):
        if status in (QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia):
            try:
                self._player.mediaStatusChanged.disconnect(self._on_media_ready)
            except RuntimeError:
                pass
            self._player.setPosition(self._pending_seek_ms)
            self._player.play()
            self._preview_timer.start(7000)
            self.stop_preview_btn.setEnabled(True)
            self.preview_chapter_btn.setEnabled(False)

    def _on_stop_preview(self):
        self._player.stop()
        self._player.setSource(QUrl())
        self._preview_timer.stop()
        self.stop_preview_btn.setEnabled(False)
        self.preview_chapter_btn.setEnabled(True)

    def _on_tab_changed(self, index):
        self._on_stop_preview()

    def _on_save_chapters(self):
        if not self._current_book:
            return

        self._player.stop()
        self._player.setSource(QUrl())
        self._preview_timer.stop()
        self.stop_preview_btn.setEnabled(False)
        self.preview_chapter_btn.setEnabled(True)

        book = self._current_book
        row_count = self.chapters_table.rowCount()
        if row_count == 0:
            return

        if len(self._chapters) != row_count:
            QMessageBox.warning(self, "Error", "Chapter count mismatch.")
            return

        titles = []
        for i in range(row_count):
            title_item = self.chapters_table.item(i, 2)
            titles.append(title_item.text() if title_item else f"Chapter {i + 1}")
        self._run_background(
            rewrite_chapters, book.file_path, list(self._chapters), titles,
            on_result=lambda _result, target=book: self._chapter_save_finished(target),
            on_error=lambda error: QMessageBox.warning(self, "Chapter Save Failed", error),
            button=self.save_chapters_btn,
        )

    def _chapter_save_finished(self, book: AudioBook):
        if self._current_book is not book:
            return
        QMessageBox.information(self, "Success", "Chapter names saved.")
        self._load_chapters(book)