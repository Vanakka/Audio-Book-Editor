import os
import threading
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox, QDialog, QListWidget, QTableWidgetItem
from PySide6.QtCore import QThread

from core.models import AudioBook, MetadataResult
from ui.detail_panel import DetailPanel
from ui.main_window import MainWindow
from ui.workers import SaveWorker


class FakeConfig:
    def get(self, key, default=None):
        return "" if key in ("last_root_folder", "libation_export_path") else default

    def set(self, key, value):
        pass

    def save(self):
        pass


class AuditUIRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_save_uses_captured_values_and_preserves_edits_during_write(self):
        book = AudioBook("synthetic.m4b", ".", title="Original")
        book.snapshot()
        book.title = "Submitted title"
        book.check_modified()
        started = threading.Event()
        release = threading.Event()
        submitted = []

        def write_captured(saved_book):
            submitted.append(saved_book)
            started.set()
            release.wait(2)
            saved_book.snapshot()
            return True

        worker = SaveWorker([book])
        with patch("ui.workers.write_tags", side_effect=write_captured):
            worker.start()
            self.assertTrue(started.wait(2))
            book.title = "New edit during save"
            book.check_modified()
            release.set()
            self.assertTrue(worker.wait(2000))
            self.assertEqual(book._original_values["title"], "Original")
            self.app.processEvents()

        self.assertIsNot(submitted[0], book)
        self.assertEqual(submitted[0].title, "Submitted title")
        self.assertEqual(book.title, "New edit during save")
        self.assertEqual(book._original_values["title"], "Submitted title")
        self.assertTrue(book.is_modified)
        worker.deleteLater()

    @patch("ui.main_window.Config", FakeConfig)
    def test_blocking_save_acknowledges_captured_values_on_ui_thread(self):
        window = MainWindow()
        book = AudioBook("synthetic.m4b", ".", title="Original")
        book.snapshot()
        book.title = "Submitted title"
        book.check_modified()
        checked_threads = []
        original_check = book.check_modified

        def record_check():
            checked_threads.append(QThread.currentThread())
            original_check()

        # Assign after constructing the worker copy so it remains plain data.
        original_factory = window._make_save_worker

        def make_worker(books):
            worker = original_factory(books)
            book.check_modified = record_check
            return worker

        def write_captured(saved_book):
            saved_book.snapshot()
            return True

        with patch.object(window, "_make_save_worker", side_effect=make_worker), \
                patch("ui.workers.write_tags", side_effect=write_captured):
            failures = window._save_books_blocking([book])

        self.assertEqual(failures, [])
        self.assertEqual(book._original_values["title"], "Submitted title")
        self.assertFalse(book.is_modified)
        self.assertEqual(checked_threads, [self.app.thread()])
        window._stop_background_workers()
        self.app.processEvents()
        window.deleteLater()

    def test_failed_save_keeps_original_baseline(self):
        book = AudioBook("synthetic.m4b", ".", title="Original")
        book.snapshot()
        book.title = "Changed"
        book.check_modified()
        worker = SaveWorker([book])
        with patch("ui.workers.write_tags", return_value=False):
            worker.run()

        self.assertEqual(book._original_values["title"], "Original")
        self.assertTrue(book.is_modified)
        worker.deleteLater()

    def test_save_captures_edits_before_worker_starts(self):
        book = AudioBook("synthetic.m4b", ".", title="Original")
        book.snapshot()
        book.title = "Submitted title"
        book.check_modified()
        worker = SaveWorker([book])
        book.title = "Edit after clicking Save"
        book.check_modified()

        def write_captured(saved_book):
            self.assertEqual(saved_book.title, "Submitted title")
            saved_book.snapshot()
            return True

        with patch("ui.workers.write_tags", side_effect=write_captured):
            worker.run()

        self.assertEqual(book._original_values["title"], "Submitted title")
        self.assertTrue(book.is_modified)
        worker.deleteLater()

    @patch("ui.main_window.Config", FakeConfig)
    @patch.object(DetailPanel, "_load_chapters", lambda self, book: None)
    def test_identifier_edits_survive_selection_changes(self):
        window = MainWindow()
        book = AudioBook("synthetic.m4b", ".", title="Original")
        book.snapshot()
        window._books = [book]
        window.detail_panel.set_book(book)

        window.detail_panel.asin_edit.setText("B012345678")
        window.detail_panel.cdek_edit.setText("B087654321")
        window.detail_panel.set_book(AudioBook("other.m4b", "."))
        window.detail_panel.set_book(book)

        self.assertEqual(book.asin_tag, "B012345678")
        self.assertEqual(book.cdek_tag, "B087654321")
        self.assertTrue(book.is_modified)
        self.assertEqual(window.detail_panel.asin_edit.text(), "B012345678")
        window.deleteLater()

    @patch("ui.main_window.Config", FakeConfig)
    @patch.object(DetailPanel, "_load_chapters", lambda self, book: None)
    def test_batch_fetch_refreshes_editor_before_save(self):
        window = MainWindow()
        book = AudioBook("synthetic.m4b", ".")
        book.snapshot()
        window._books = [book]
        window.detail_panel.set_book(book)
        window._on_batch_fetch_result(
            book, MetadataResult(source="test", title="Fetched title")
        )
        window.detail_panel._sync_to_book()

        self.assertEqual(book.title, "Fetched title")
        self.assertEqual(window.detail_panel.title_edit.text(), "Fetched title")
        self.assertTrue(book.is_modified)
        window.deleteLater()

    @patch("ui.main_window.Config", FakeConfig)
    @patch.object(DetailPanel, "_load_chapters", lambda self, book: None)
    def test_batch_fetch_preserves_current_book_cover_and_editor_drafts(self):
        window = MainWindow()
        book = AudioBook("synthetic.m4b", ".")
        book.snapshot()
        window._books = [book]
        window.library_panel.set_books([book])
        panel = window.detail_panel
        panel.set_book(book)
        panel._chapters = [{"start_time": "0", "end_time": "5", "tags": {"title": "Original"}}]
        panel.chapters_table.setRowCount(1)
        panel.chapters_table.setItem(0, 2, QTableWidgetItem("Draft chapter title"))
        panel.filename_edit.setText("Pending custom filename.m4b")
        panel.cover_search_edit.setText("Custom cover search")

        with patch.object(panel, "_load_chapters") as load_chapters, \
                patch.object(panel.cover_widget, "set_cover") as set_cover:
            window._on_batch_fetch_result(
                book, MetadataResult(source="test", title="Fetched title")
            )

        self.assertEqual(book.title, "Fetched title")
        self.assertEqual(panel.title_edit.text(), "Fetched title")
        self.assertEqual(panel.chapters_table.item(0, 2).text(), "Draft chapter title")
        self.assertEqual(panel.filename_edit.text(), "Pending custom filename.m4b")
        self.assertEqual(panel.cover_search_edit.text(), "Custom cover search")
        load_chapters.assert_not_called()
        set_cover.assert_not_called()
        window.deleteLater()

    @patch("ui.main_window.Config", FakeConfig)
    def test_save_all_does_not_start_another_save_for_active_book(self):
        window = MainWindow()
        book = AudioBook("synthetic.m4b", ".", title="Original")
        book.snapshot()
        book.title = "Changed"
        book.check_modified()
        window._books = [book]
        started = threading.Event()
        release = threading.Event()

        def wait_for_release(saved_book):
            started.set()
            release.wait(2)
            saved_book.snapshot()
            return True

        with patch("ui.workers.write_tags", side_effect=wait_for_release) as write_tags, \
                patch("ui.main_window.BatchDialog") as batch_dialog:
            window._on_save_book(book)
            self.assertTrue(started.wait(2))
            window._on_save_all_modified()
            release.set()
            for worker in window.findChildren(SaveWorker):
                self.assertTrue(worker.wait(2000))
            self.app.processEvents()

        self.assertEqual(write_tags.call_count, 1)
        batch_dialog.assert_not_called()
        window.deleteLater()

    @patch("ui.main_window.Config", FakeConfig)
    def test_finished_save_keeps_path_claim_until_ui_callbacks_finish(self):
        window = MainWindow()
        book = AudioBook("synthetic.m4b", ".", title="Original")
        book.snapshot()
        book.title = "First submission"
        book.check_modified()

        def write_captured(saved_book):
            saved_book.snapshot()
            return True

        with patch("ui.workers.write_tags", side_effect=write_captured) as write_tags:
            window._on_save_book(book)
            worker = next(iter(window._active_save_workers))
            self.assertTrue(worker.wait(2000))
            book.title = "Second submission"
            book.check_modified()
            window._on_save_book(book)
            for active in list(window._active_save_workers):
                self.assertTrue(active.wait(2000))
            self.app.processEvents()

        self.assertEqual(write_tags.call_count, 1)
        self.assertEqual(book._original_values["title"], "First submission")
        self.assertTrue(book.is_modified)
        window.deleteLater()

    @patch("ui.main_window.Config", FakeConfig)
    def test_blocking_save_waits_for_native_thread_completion(self):
        window = MainWindow()
        book = AudioBook("synthetic.m4b", ".", title="Original")
        book.snapshot()
        book.title = "Submitted title"
        book.check_modified()
        release = threading.Event()

        class DelayedSaveWorker(SaveWorker):
            def run(self):
                super().run()
                release.wait(2)

        def write_captured(saved_book):
            saved_book.snapshot()
            return True

        timer = threading.Timer(0.05, release.set)
        timer.start()
        with patch("ui.main_window.SaveWorker", DelayedSaveWorker), \
                patch("ui.workers.write_tags", side_effect=write_captured):
            failures = window._save_books_blocking([book])
            active_workers = list(window._active_save_workers)
            release.set()
            for worker in active_workers:
                worker.wait(2000)
        timer.join(2)

        self.assertEqual(failures, [])
        self.assertEqual(active_workers, [])
        self.assertEqual(window._saving_paths, set())
        self.app.processEvents()
        window.deleteLater()

    @patch("ui.main_window.Config", FakeConfig)
    @patch.object(DetailPanel, "_load_chapters", lambda self, book: None)
    def test_cancelled_rescan_keeps_dirty_library_and_editor(self):
        window = MainWindow()
        book = AudioBook("synthetic.m4b", ".", title="Original")
        book.snapshot()
        book.title = "Unsaved edit"
        book.check_modified()
        window._books = [book]
        window.detail_panel.set_book(book)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.Cancel), \
                patch("ui.main_window.ScanWorker") as scan_worker:
            window._scan_folder("synthetic-root")

        scan_worker.assert_not_called()
        self.assertEqual(window._books, [book])
        self.assertIs(window.detail_panel._current_book, book)
        self.assertEqual(window.detail_panel.title_edit.text(), "Unsaved edit")
        window.deleteLater()

    @patch("ui.main_window.Config", FakeConfig)
    def test_cancelled_open_does_not_persist_new_root(self):
        window = MainWindow()
        window.config.set = Mock()
        window.config.save = Mock()
        with patch("ui.main_window.QFileDialog.getExistingDirectory", return_value="synthetic-root"), \
                patch.object(window, "_scan_folder", return_value=False):
            window._on_open_folder()

        window.config.set.assert_not_called()
        window.config.save.assert_not_called()
        window.deleteLater()

    @patch("ui.main_window.Config", FakeConfig)
    def test_failed_save_before_rescan_keeps_library(self):
        window = MainWindow()
        book = AudioBook("synthetic.m4b", ".", title="Original")
        book.snapshot()
        book.title = "Changed"
        book.check_modified()
        window._books = [book]

        with patch.object(QMessageBox, "question", return_value=QMessageBox.Save), \
                patch.object(QMessageBox, "warning"), \
                patch("ui.workers.write_tags", return_value=False), \
                patch("ui.main_window.ScanWorker") as scan_worker:
            self.assertFalse(window._scan_folder("synthetic-root"))

        scan_worker.assert_not_called()
        self.assertTrue(book.is_modified)
        self.assertEqual(window._books, [book])
        window._stop_background_workers()
        self.app.processEvents()
        window.deleteLater()

    @patch("ui.main_window.Config", FakeConfig)
    def test_save_before_rescan_writes_and_acknowledges_dirty_book(self):
        window = MainWindow()
        book = AudioBook("synthetic.m4b", ".", title="Original")
        book.snapshot()
        book.title = "Changed"
        book.check_modified()
        window._books = [book]

        def write_captured(saved_book):
            saved_book.snapshot()
            return True

        with patch.object(QMessageBox, "question", return_value=QMessageBox.Save), \
                patch("ui.workers.write_tags", side_effect=write_captured) as write_tags, \
                patch("ui.main_window.ScanWorker") as scan_worker:
            self.assertTrue(window._scan_folder("synthetic-root"))

        write_tags.assert_called_once()
        scan_worker.return_value.start.assert_called_once()
        self.assertEqual(book._original_values["title"], "Changed")
        self.assertFalse(book.is_modified)
        window._stop_background_workers()
        self.app.processEvents()
        window.deleteLater()

    @patch("ui.main_window.Config", FakeConfig)
    def test_discard_before_rescan_does_not_write_tags(self):
        window = MainWindow()
        book = AudioBook("synthetic.m4b", ".", title="Original")
        book.snapshot()
        book.title = "Changed"
        book.check_modified()
        window._books = [book]

        with patch.object(QMessageBox, "question", return_value=QMessageBox.Discard), \
                patch("ui.workers.write_tags") as write_tags, \
                patch("ui.main_window.ScanWorker") as scan_worker:
            self.assertTrue(window._scan_folder("synthetic-root"))

        write_tags.assert_not_called()
        scan_worker.return_value.start.assert_called_once()
        window.deleteLater()

    @patch("ui.main_window.Config", FakeConfig)
    def test_new_edits_during_save_on_close_keep_window_open(self):
        window = MainWindow()
        book = AudioBook("synthetic.m4b", ".", title="Original")
        book.snapshot()
        book.title = "Changed"
        book.check_modified()
        window._books = [book]
        event = Mock()

        def save_then_edit(books):
            book.snapshot()
            book.title = "New edit during save"
            book.check_modified()
            return []

        with patch.object(QMessageBox, "question", return_value=QMessageBox.Save), \
                patch.object(window, "_save_books_blocking", side_effect=save_then_edit):
            window.closeEvent(event)

        event.ignore.assert_called_once()
        self.assertTrue(book.is_modified)
        window.deleteLater()

    @patch("ui.main_window.Config", FakeConfig)
    @patch.object(DetailPanel, "_load_chapters", lambda self, book: None)
    def test_late_asin_search_cannot_change_another_book(self):
        window = MainWindow()
        first = AudioBook("first.m4b", ".", title="First")
        second = AudioBook("second.m4b", ".", title="Second")
        first.snapshot()
        second.snapshot()
        panel = window.detail_panel
        panel.set_book(first)
        callbacks = []

        def capture_search(*args, **kwargs):
            callbacks.append(kwargs["on_result"])

        class AcceptedDialog(QDialog):
            def exec(self):
                self.findChildren(QListWidget)[0].setCurrentRow(0)
                return QDialog.Accepted

        with patch.object(panel, "_run_background", side_effect=capture_search), \
                patch("ui.detail.details_tab.QDialog", AcceptedDialog):
            panel._on_asin_search()
            panel.set_book(second)
            callbacks[0]([{"asin": "B012345678", "title": "First"}])

        self.assertEqual(second.asin_tag, "")
        self.assertEqual(second.identifier, "")
        self.assertFalse(second.is_modified)
        window.deleteLater()


if __name__ == "__main__":
    unittest.main()
