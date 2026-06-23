import unittest
from unittest.mock import patch

from core.models import AudioBook
from core.models import MetadataResult
from ui.workers import FetchWorker, SaveWorker, ScanWorker


class WorkerCancellationTests(unittest.TestCase):
    @patch("ui.workers.write_tags")
    def test_save_worker_can_be_cancelled_before_writing(self, write_tags):
        worker = SaveWorker([AudioBook("book.m4b", ".")])
        worker.cancel()
        worker.run()
        write_tags.assert_not_called()

    @patch("ui.workers.populate_book_from_tags")
    @patch("ui.workers.scan_directory")
    def test_cancelled_scan_emits_only_processed_books(self, scan_directory, populate):
        scan_directory.return_value = [
            AudioBook("one.m4b", "."), AudioBook("two.m4b", ".")
        ]
        emitted = []
        worker = ScanWorker(".")
        worker.finished_signal.connect(emitted.append)
        worker.cancel()
        worker.run()

        self.assertEqual(emitted, [[]])
        populate.assert_not_called()

    def test_fetch_worker_reports_actual_success_and_error_counts(self):
        class Scraper:
            def supports_identifier_type(self, _kind):
                return True
            def fetch(self, _identifier, _kind, title_hint="", author_hint=""):
                if title_hint == "bad":
                    raise RuntimeError("provider failed")
                return MetadataResult(source="test", title=title_hint)

        books = [
            AudioBook("one.m4b", ".", title="good"),
            AudioBook("two.m4b", ".", title="bad"),
        ]
        counts = []
        worker = FetchWorker(books, [Scraper()])
        worker.finished_signal.connect(lambda success, errors: counts.append((success, errors)))
        worker.run()

        self.assertEqual(counts, [(1, 1)])


if __name__ == "__main__":
    unittest.main()
