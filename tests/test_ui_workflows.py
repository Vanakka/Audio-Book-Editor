import os
import time
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication, QMessageBox, QScrollArea

from core.models import AudioBook, MetadataResult
from ui.fetch_dialog import FetchDialog
from ui.main_window import MainWindow


class FakeConfig:
    def get(self, key, default=None):
        return "" if key in ("last_root_folder", "libation_export_path") else default
    def set(self, key, value):
        pass
    def save(self):
        pass


class MainWindowWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @patch("ui.main_window.Config", FakeConfig)
    def test_failed_save_on_close_keeps_window_open(self):
        window = MainWindow()
        book = AudioBook("book.m4b", ".", title="Changed")
        book.snapshot()
        book.title = "Changed again"
        book.check_modified()
        window._books = [book]
        event = Mock()

        with patch.object(QMessageBox, "question", return_value=QMessageBox.Save), \
                patch.object(QMessageBox, "warning"), \
                patch("ui.main_window.write_tags", return_value=False), \
                patch.object(window, "_stop_background_workers", return_value=True):
            window.closeEvent(event)

        event.ignore.assert_called_once()
        window.deleteLater()

    @patch("ui.main_window.Config", FakeConfig)
    def test_save_book_writes_metadata_off_the_ui_thread(self):
        window = MainWindow()
        book = AudioBook("book.m4b", ".", title="Changed")
        writer_threads = []

        def record_writer_thread(_book):
            writer_threads.append(QThread.currentThread())
            return True

        with patch("ui.main_window.write_tags", side_effect=record_writer_thread), \
                patch("ui.workers.write_tags", side_effect=record_writer_thread), \
                patch.object(window.library_panel, "refresh_current"):
            window._on_save_book(book)
            deadline = time.monotonic() + 2
            while not writer_threads and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(0.01)

        self.assertTrue(writer_threads, "save worker never called write_tags")
        self.assertIsNot(writer_threads[0], self.app.thread())
        window._stop_background_workers()
        window.deleteLater()

    def test_source_header_selects_every_available_value_in_column(self):
        book = AudioBook(
            "book.m4b", ".", title="Current title", author="Current author"
        )
        result = MetadataResult(
            source="Audible API",
            title="Fetched title",
            author="",
            series="Fetched series",
        )

        with patch.object(FetchDialog, "_setup_ui"), \
                patch.object(FetchDialog, "_start_fetch"):
            dialog = FetchDialog(book, [])
        dialog.scroll = QScrollArea()
        dialog._source_names = ["Audible API"]
        dialog._results = {"Audible API": result}
        dialog._build_rows()

        dialog._select_source(1)

        self.assertEqual(dialog._selected["title"], 1)
        self.assertEqual(dialog._selected["series"], 1)
        self.assertEqual(dialog._selected["author"], 0)
        self.assertTrue(dialog._source_checks[1].isChecked())

        dialog._select_cell("title", 0)
        self.assertFalse(dialog._source_checks[1].isChecked())
        dialog.deleteLater()


if __name__ == "__main__":
    unittest.main()
