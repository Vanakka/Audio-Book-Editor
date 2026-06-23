import threading
import time
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from core.metadata import write_cover, write_tags
from core.models import AudioBook


class MetadataWriteTests(unittest.TestCase):
    @patch("core.metadata.MP4")
    def test_clearing_fields_deletes_existing_standard_and_identifier_tags(self, mp4_class):
        fake = Mock()
        fake.tags = {
            "\xa9nam": ["Old title"],
            "asin": ["OLD"],
            "CDEK": ["OLD"],
            "----:com.pilabor.tone:AUDIBLE_ASIN": [b"OLD"],
        }
        mp4_class.return_value = fake
        book = AudioBook("book.m4b", ".")

        self.assertTrue(write_tags(book))

        self.assertNotIn("\xa9nam", fake.tags)
        self.assertNotIn("asin", fake.tags)
        self.assertNotIn("CDEK", fake.tags)
        self.assertNotIn("----:com.pilabor.tone:AUDIBLE_ASIN", fake.tags)

    @patch("core.metadata.MP4")
    def test_invalid_cover_bytes_are_rejected_before_opening_audio(self, mp4_class):
        book = AudioBook("book.m4b", ".")
        self.assertFalse(write_cover(book, b"not an image", "jpeg"))
        mp4_class.assert_not_called()

    def test_tag_and_cover_writes_to_same_file_are_serialized(self):
        state_guard = threading.Lock()
        start_gate = threading.Barrier(2)
        state = {"active": 0, "max_active": 0}

        class FakeMP4:
            def __init__(self, _path):
                self.tags = {}

            def add_tags(self):
                self.tags = {}

            def save(self):
                with state_guard:
                    state["active"] += 1
                    state["max_active"] = max(state["max_active"], state["active"])
                time.sleep(0.05)
                with state_guard:
                    state["active"] -= 1

        book = AudioBook("same-book.m4b", ".", title="Changed")
        results = []

        def save_tags():
            start_gate.wait()
            results.append(write_tags(book))

        def save_cover():
            start_gate.wait()
            results.append(write_cover(book, b"cover", "jpeg"))

        with tempfile.TemporaryDirectory() as cache_dir, \
                patch("core.metadata.MP4", FakeMP4), \
                patch("core.metadata.MP4Cover", side_effect=lambda data, imageformat: data), \
                patch("core.metadata._prepare_cover_bytes", return_value=(b"cover", "jpeg")), \
                patch("core.metadata.COVERS_DIR", Path(cache_dir)):
            threads = [threading.Thread(target=save_tags), threading.Thread(target=save_cover)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(2)

        self.assertCountEqual(results, [True, True])
        self.assertEqual(state["max_active"], 1)


if __name__ == "__main__":
    unittest.main()
