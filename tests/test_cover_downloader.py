import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from PIL import Image

import scrapers.cover_downloader as covers


def jpeg_bytes(color):
    output = BytesIO()
    Image.new("RGB", (2, 2), color).save(output, "JPEG")
    return output.getvalue()


def jpeg_response(color):
    response = Mock(status_code=200, headers={})
    response.iter_content.return_value = [jpeg_bytes(color)]
    response.raise_for_status.return_value = None
    return response


class CoverDownloaderTests(unittest.TestCase):
    def test_identifierless_books_do_not_share_a_cache_entry(self):
        first_response = jpeg_response("red")
        second_response = jpeg_response("blue")

        with TemporaryDirectory() as root, \
                patch.object(covers, "COVERS_DIR", Path(root)), \
                patch.object(covers.requests, "get", side_effect=[first_response, second_response]):
            first = covers.download_cover("https://example.test/one.jpg", "")
            second = covers.download_cover("https://example.test/two.jpg", "")

        self.assertNotEqual(first, second)

    def test_force_replaces_an_existing_identifier_cache_entry(self):
        first_response = jpeg_response("red")
        second_response = jpeg_response("blue")

        with TemporaryDirectory() as root, \
                patch.object(covers, "COVERS_DIR", Path(root)), \
                patch.object(covers.requests, "get", side_effect=[first_response, second_response]) as get:
            first = covers.download_cover("https://example.test/one.jpg", "ASIN")
            second = covers.download_cover("https://example.test/two.jpg", "ASIN", force=True)
            final_bytes = Path(second).read_bytes()

        self.assertEqual(first, second)
        self.assertEqual(get.call_count, 2)
        self.assertEqual(Image.open(BytesIO(final_bytes)).getpixel((0, 0))[2] > 100, True)


if __name__ == "__main__":
    unittest.main()
