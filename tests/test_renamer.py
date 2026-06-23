import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.models import AudioBook
from core.renamer import rename_to_filename


class FileRenameTests(unittest.TestCase):
    def test_manual_rename_rejects_parent_traversal(self):
        with TemporaryDirectory() as root:
            root = Path(root)
            source = root / "book.m4b"
            source.write_bytes(b"audio")
            book = AudioBook(str(source), str(root))

            self.assertFalse(rename_to_filename(book, "..\\escaped.m4b"))
            self.assertTrue(source.exists())


if __name__ == "__main__":
    unittest.main()
