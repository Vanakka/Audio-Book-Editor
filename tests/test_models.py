import unittest

from core.models import AudioBook


class AudioBookStateTests(unittest.TestCase):
    def test_identifier_fields_are_tracked_and_reverted(self):
        book = AudioBook(
            "book.m4b", ".", identifier="OLD", identifier_type="asin",
            asin_tag="OLD", cdek_tag="OLD",
        )
        book.snapshot()

        book.identifier = "NEW"
        book.asin_tag = "NEW"
        book.cdek_tag = "NEW"
        book.check_modified()

        self.assertTrue(book.is_modified)
        book.revert()
        self.assertEqual((book.identifier, book.asin_tag, book.cdek_tag), ("OLD", "OLD", "OLD"))


if __name__ == "__main__":
    unittest.main()
