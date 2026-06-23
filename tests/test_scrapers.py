import unittest
from unittest.mock import Mock, patch

from scrapers.google_books import GoogleBooksScraper


class ScraperSelectionTests(unittest.TestCase):
    @patch("scrapers.google_books.get_with_retry")
    def test_google_books_skips_unrelated_first_result(self, get):
        response = Mock()
        response.json.return_value = {
            "totalItems": 2,
            "items": [
                {"volumeInfo": {"title": "A Wish Upon a Star", "authors": ["Other Author"]}},
                {"volumeInfo": {"title": "Wish Upon the Stars 7", "authors": ["Malcolm Tent"]}},
            ],
        }
        get.return_value = response

        result = GoogleBooksScraper().fetch(
            "", "unknown", "Wish Upon the Stars 7: A Superhero Cultivation LitRPG", "Malcom Tent"
        )

        self.assertEqual(result.title, "Wish Upon the Stars 7")


if __name__ == "__main__":
    unittest.main()
