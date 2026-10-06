import os
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox, QTableWidgetItem

from core.models import AudioBook
from core.renamer import execute_renames
from tests.test_audit_ui import FakeConfig
from ui.detail_panel import DetailPanel
from ui.main_window import MainWindow


class RenameUIAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root / "original"
        self.nested = self.original / "nested"
        self.outside = self.root / "outside"
        self.nested.mkdir(parents=True)
        self.outside.mkdir()
        self.selected = self.make_book(self.original, "one.m4b", "Selected", "Selected series")
        self.sibling = self.make_book(self.original, "two.m4b", "Sibling", "Other series")
        self.descendant = self.make_book(self.nested, "three.m4b", "Nested", "Nested series")
        self.unselected = self.make_book(self.outside, "four.m4b", "Outside", "Outside series")
        with patch("ui.main_window.Config", FakeConfig), \
                patch.object(DetailPanel, "_load_chapters", lambda self, book: None):
            self.window = MainWindow()
            self.window._books = [self.selected, self.sibling, self.descendant, self.unselected]
            self.window.library_panel.set_books(self.window._books)
            self.window.detail_panel.set_book(self.sibling)
        self.addCleanup(self.cleanup_window)
        self.selection = patch.object(self.window.library_panel, "get_selected_books", return_value=[self.selected])
        self.selection.start()
        self.addCleanup(self.selection.stop)
        self.dialog_books = []
        self.operation_order = []

    def cleanup_window(self):
        self.window._stop_background_workers()
        self.app.processEvents()
        self.window.deleteLater()
        self.app.processEvents()

    @staticmethod
    def make_book(folder, name, title, series):
        file_path = folder / name
        file_path.write_bytes(b"synthetic media bytes")
        book = AudioBook(str(file_path), str(folder), title=title, series=series)
        book.snapshot()
        return book

    def rename_dialog(self, books, parent):
        self.dialog_books.append(list(books))
        owner = self

        class Dialog:
            renames_completed = Mock()

            def exec(self):
                owner.assertEqual(owner.window._active_save_workers, set())
                owner.operation_order.append("rename")
                success, errors = execute_renames(books, "{series}")
                owner.assertEqual((success, errors), (1, 0))
                return 1

        return Dialog()

    def make_sibling_dirty(self):
        self.window.detail_panel.title_edit.setText("Unsaved sibling title")

    def test_cancel_prevents_folder_move(self):
        self.make_sibling_dirty()
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Cancel), \
                patch("ui.main_window.RenameDialog", side_effect=self.rename_dialog):
            self.window._on_rename()

        self.assertTrue(self.original.is_dir())
        self.assertFalse((self.root / "Selected series").exists())
        self.assertEqual(self.dialog_books, [])
        self.assertTrue(self.sibling.is_modified)

    def test_selected_folder_move_updates_unselected_siblings_and_descendants(self):
        self.make_sibling_dirty()
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Discard), \
                patch("ui.main_window.RenameDialog", side_effect=self.rename_dialog):
            self.window._on_rename()

        moved = self.root / "Selected series"
        self.assertEqual(self.dialog_books, [[self.selected]])
        self.assertEqual(self.sibling.folder_path, str(moved))
        self.assertEqual(self.sibling.file_path, str(moved / "two.m4b"))
        self.assertEqual(self.descendant.folder_path, str(moved / "nested"))
        self.assertEqual(self.descendant.file_path, str(moved / "nested" / "three.m4b"))
        for book in self.window._books:
            self.assertTrue(Path(book.file_path).is_file())
        self.assertEqual(self.unselected.folder_path, str(self.outside))
        self.assertTrue(self.outside.is_dir())
        self.assertFalse(self.sibling.is_modified)
        self.assertEqual(self.sibling.title, "Sibling")
        self.assertIn(str(moved / "two.m4b"), self.window.detail_panel.file_info_label.text())
        self.assertEqual(self.window.detail_panel.current_filename_label.text(), "two.m4b")

    def test_save_failure_prevents_folder_move(self):
        self.make_sibling_dirty()
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Save), \
                patch.object(QMessageBox, "warning"), \
                patch("ui.workers.write_tags", return_value=False), \
                patch("ui.main_window.RenameDialog", side_effect=self.rename_dialog):
            self.window._on_rename()

        self.assertTrue(self.original.is_dir())
        self.assertEqual(self.dialog_books, [])
        self.assertTrue(self.sibling.is_modified)

    def test_save_finishes_at_original_path_before_folder_move(self):
        self.make_sibling_dirty()

        def write_captured(book):
            self.operation_order.append("save")
            self.assertTrue(Path(book.file_path).is_file())
            self.assertEqual(Path(book.file_path).parent, self.original)
            book.snapshot()
            return True

        with patch.object(QMessageBox, "question", return_value=QMessageBox.Save), \
                patch("ui.workers.write_tags", side_effect=write_captured), \
                patch("ui.main_window.RenameDialog", side_effect=self.rename_dialog):
            self.window._on_rename()

        self.assertEqual(self.operation_order, ["save", "rename"])
        self.assertFalse(self.sibling.is_modified)
        self.assertEqual(self.sibling.title, "Unsaved sibling title")

    def test_busy_worker_prevents_folder_move(self):
        with patch.object(self.window, "_stop_background_workers", return_value=False), \
                patch("ui.main_window.RenameDialog", side_effect=self.rename_dialog):
            self.window._on_rename()

        self.assertTrue(self.original.is_dir())
        self.assertEqual(self.dialog_books, [])

    def test_active_save_finishes_before_folder_move(self):
        self.make_sibling_dirty()
        started = threading.Event()
        release = threading.Event()

        def write_captured(book):
            self.operation_order.append("save")
            started.set()
            release.wait(2)
            self.assertTrue(Path(book.file_path).is_file())
            book.snapshot()
            return True

        with patch("ui.workers.write_tags", side_effect=write_captured), \
                patch.object(QMessageBox, "question") as question, \
                patch("ui.main_window.RenameDialog", side_effect=self.rename_dialog):
            self.window._on_save_book(self.sibling)
            self.assertTrue(started.wait(2))
            timer = threading.Timer(0.05, release.set)
            timer.start()
            self.window._on_rename()
            timer.join(2)

        question.assert_not_called()
        self.assertEqual(self.operation_order, ["save", "rename"])
        self.assertTrue(Path(self.sibling.file_path).is_file())
        self.assertFalse(self.sibling.is_modified)

    def test_discard_tags_and_rename_preserve_cover_and_editor_drafts(self):
        self.make_sibling_dirty()
        panel = self.window.detail_panel
        self.sibling.cover_path = "synthetic-cover.jpg"
        self.sibling.has_embedded_cover = True
        panel._chapters = [{"start_time": "0", "end_time": "5", "tags": {"title": "Original"}}]
        panel.chapters_table.setRowCount(1)
        panel.chapters_table.setItem(0, 2, QTableWidgetItem("Draft chapter title"))
        panel.filename_edit.setText("Pending custom filename.m4b")

        with patch.object(QMessageBox, "question", return_value=QMessageBox.Discard), \
                patch.object(panel, "_load_chapters") as load_chapters, \
                patch.object(panel.cover_widget, "set_cover") as set_cover, \
                patch("ui.main_window.RenameDialog", side_effect=self.rename_dialog):
            self.window._on_rename()

        self.assertEqual(self.sibling.title, "Sibling")
        self.assertEqual(panel.title_edit.text(), "Sibling")
        self.assertEqual(self.sibling.cover_path, "synthetic-cover.jpg")
        self.assertTrue(self.sibling.has_embedded_cover)
        self.assertEqual(panel.chapters_table.item(0, 2).text(), "Draft chapter title")
        self.assertEqual(panel.filename_edit.text(), "Pending custom filename.m4b")
        load_chapters.assert_not_called()
        set_cover.assert_not_called()


if __name__ == "__main__":
    unittest.main()
