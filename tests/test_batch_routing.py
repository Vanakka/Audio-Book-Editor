import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from core.models import AudioBook, MetadataResult
from ui.main_window import MainWindow


class BatchRoutingTests(unittest.TestCase):
    def test_result_is_applied_to_emitting_book_not_first_matching_identifier(self):
        first = AudioBook("first.m4b", ".", identifier="")
        second = AudioBook("second.m4b", ".", identifier="")
        owner = SimpleNamespace(
            _books=[first, second],
            detail_panel=SimpleNamespace(_current_book=None),
            library_panel=Mock(),
        )

        MainWindow._on_batch_fetch_result(
            owner, second, MetadataResult(source="test", title="Second title")
        )

        self.assertEqual(first.title, "")
        self.assertEqual(second.title, "Second title")

    def test_stale_result_for_equal_book_is_not_applied(self):
        active = AudioBook("same.m4b", ".")
        stale = AudioBook("same.m4b", ".")
        owner = SimpleNamespace(
            _books=[active],
            detail_panel=SimpleNamespace(_current_book=None),
            library_panel=Mock(),
        )

        MainWindow._on_batch_fetch_result(
            owner, stale, MetadataResult(source="test", title="Stale title")
        )

        self.assertEqual(active.title, "")
        self.assertEqual(stale.title, "")
        owner.library_panel.model.refresh_row.assert_not_called()


if __name__ == "__main__":
    unittest.main()
