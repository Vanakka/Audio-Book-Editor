import unittest

from scrapers.matching import is_relevant


class MatchingTests(unittest.TestCase):
    def test_rejects_unrelated_first_result(self):
        self.assertFalse(
            is_relevant("A Wish Upon a Star", "Wish Upon the Stars 7", "Unknown", "Malcom Tent")
        )

    def test_accepts_subtitle_and_minor_author_variation(self):
        self.assertTrue(
            is_relevant(
                "Wish Upon the Stars 7",
                "Wish Upon the Stars 7: A Superhero Cultivation LitRPG",
                "Malcolm Tent",
                "Malcom Tent",
            )
        )


if __name__ == "__main__":
    unittest.main()
