import unittest
from types import SimpleNamespace

from core.models import AudioBook, MetadataResult
from ui.main_window import MainWindow


class BatchRoutingTests(unittest.TestCase):
    def test_result_is_applied_to_emitting_book_not_first_matching_identifier(self):
        first = AudioBook("first.m4b", ".", identifier="")
        second = AudioBook("second.m4b", ".", identifier="")
        owner = SimpleNamespace(_books=[first, second])

        MainWindow._on_batch_fetch_result(
            owner, second, MetadataResult(source="test", title="Second title")
        )

        self.assertEqual(first.title, "")
        self.assertEqual(second.title, "Second title")


if __name__ == "__main__":
    unittest.main()
