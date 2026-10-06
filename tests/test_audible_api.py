import unittest
from unittest.mock import Mock, patch
from scrapers.audible_api import search_catalog


class AudibleCatalogSearchTests(unittest.TestCase):
    @patch("scrapers.audible_api.requests.get")
    def test_retries_without_subtitle_and_author_when_exact_search_is_empty(self, get):
        empty = Mock()
        empty.raise_for_status.return_value = None
        empty.json.return_value = {"products": []}

        found = Mock()
        found.raise_for_status.return_value = None
        found.json.return_value = {
            "products": [
                {"asin": "B0H4HF212K", "title": "Wish Upon the Stars 1"}
            ]
        }

        get.side_effect = [empty, empty, empty, found]

        products = search_catalog(
            "Wish Upon the Stars 1: A Superhero Cultivation LitRPG",
            "Malcom Tent",
        )

        self.assertEqual(products[0]["asin"], "B0H4HF212K")
        self.assertEqual(get.call_count, 4)
        attempted_params = [call.kwargs["params"] for call in get.call_args_list]
        self.assertEqual(
            attempted_params,
            [
                {
                    "title": "Wish Upon the Stars 1: A Superhero Cultivation LitRPG",
                    "response_groups": "product_desc,contributors,series",
                    "num_results": 10,
                    "author": "Malcom Tent",
                },
                {
                    "title": "Wish Upon the Stars 1: A Superhero Cultivation LitRPG",
                    "response_groups": "product_desc,contributors,series",
                    "num_results": 10,
                },
                {
                    "title": "Wish Upon the Stars 1",
                    "response_groups": "product_desc,contributors,series",
                    "num_results": 10,
                    "author": "Malcom Tent",
                },
                {
                    "title": "Wish Upon the Stars 1",
                    "response_groups": "product_desc,contributors,series",
                    "num_results": 10,
                },
            ],
        )


if __name__ == "__main__":
    unittest.main()
