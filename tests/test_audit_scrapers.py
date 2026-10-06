"""Offline regressions for provider and cover-download audit findings."""

import unittest
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import Mock, patch

import requests
from PIL import Image

from scrapers.audible import AudibleScraper
from scrapers.audible_api import AudibleAPIScraper
import scrapers.cover_downloader as covers
from scrapers.cover_search import search_audible_covers
from scrapers.goodreads import GoodreadsScraper
from scrapers.http import get_with_retry
from scrapers.matching import is_relevant


def response(status, body=""):
    result = requests.Response()
    result.status_code = status
    result._content = body.encode()
    result._content_consumed = True
    result.url = "https://example.test"
    return result


class StreamingResponse:
    status_code = 200

    def __init__(self, chunks, headers=None):
        self.chunks = chunks
        self.headers = headers or {}
        self.content_accessed = False
        self.chunks_read = 0
        self.closed = False

    @property
    def content(self):
        self.content_accessed = True
        return b"".join(self.chunks)

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        for chunk in self.chunks:
            self.chunks_read += 1
            yield chunk

    def close(self):
        self.closed = True


class ScraperAuditTests(unittest.TestCase):
    def test_audible_catalog_404_is_no_match(self):
        with patch("scrapers.audible_api.requests.get", return_value=response(404)):
            self.assertIsNone(AudibleAPIScraper().fetch("B012345678"))

    def test_audible_page_404_is_no_match(self):
        scraper = AudibleScraper(delay=0)
        with patch.object(scraper._session, "get", return_value=response(404)):
            self.assertIsNone(scraper.fetch("B012345678"))

    def test_rejects_different_numbered_book_by_same_author(self):
        self.assertFalse(is_relevant(
            "Wish Upon the Stars 1", "Wish Upon the Stars 7",
            "Malcolm Tent", "Malcolm Tent",
        ))

    def test_exact_non_latin_title_matches(self):
        self.assertTrue(is_relevant("三体", "三体", "刘慈欣", "刘慈欣"))

    def test_title_number_guard_preserves_subtitle_and_year_variations(self):
        self.assertTrue(is_relevant("Dune", "Dune: 50 Years of Influence"))
        self.assertTrue(is_relevant("An Illustrated History of Dune 1965", "An Illustrated History of Dune 2020"))
        self.assertTrue(is_relevant("Series 1.5", "Series 1.50: A Novel"))

    def test_rejects_different_explicit_volume_numbers(self):
        self.assertFalse(is_relevant("Dune Book 1", "Dune Book 2: A Novel"))

    def test_goodreads_revalidates_the_fetched_book_page(self):
        scraper = GoodreadsScraper(delay=0)
        search_html = '<tr><td><a class="bookTitle" href="/book/show/1">Dune</a></td></tr>'
        wrong_book_html = '<h1 data-testid="bookTitle">Sign in</h1>'
        with patch.object(scraper._session, "get", side_effect=[
            response(200, search_html), response(200, wrong_book_html),
        ]):
            self.assertIsNone(scraper.fetch("", "unknown", "Dune"))

    def test_audible_api_product_without_title_is_no_match(self):
        payload = '{"product": {"asin": "B012345678", "title": ""}}'
        with patch("scrapers.audible_api.requests.get", return_value=response(200, payload)):
            self.assertIsNone(AudibleAPIScraper().fetch("B012345678"))

    def test_ten_letter_title_uses_cover_catalog_search(self):
        product = {"title": "Foundation", "product_images": {"500": "https://example.test/cover"}}
        with patch("scrapers.cover_search.search_catalog", return_value=[product]) as search, \
                patch("scrapers.cover_search.get_with_retry", side_effect=AssertionError("Title sent to ASIN lookup")):
            result = search_audible_covers("Foundation", "Isaac Asimov")
        self.assertEqual(result[0]["title"], "Foundation")
        self.assertEqual(search.call_args.args[:2], ("Foundation", "Isaac Asimov"))

    def test_cover_asin_lookup_remains_direct(self):
        payload = '{"product": {"title": "Dune", "product_images": {"500": "https://example.test/cover"}}}'
        with patch("scrapers.cover_search.search_catalog") as search, \
                patch("scrapers.cover_search.requests.get", return_value=response(200, payload)) as get:
            result = search_audible_covers("b012345678")
        self.assertEqual(result[0]["title"], "Dune")
        search.assert_not_called()
        self.assertTrue(get.call_args.args[0].endswith("/B012345678"))

    def test_cover_size_limit_stops_the_response_stream(self):
        download = StreamingResponse([b"a" * 8] * 10)
        with TemporaryDirectory() as root, \
                patch.object(covers, "COVERS_DIR", Path(root)), \
                patch.object(covers, "MAX_COVER_BYTES", 20), \
                patch.object(covers.requests, "get", return_value=download) as get:
            self.assertIsNone(covers.download_cover("https://example.test/image", "test"))
            self.assertFalse(download.content_accessed)
            self.assertEqual(download.chunks_read, 3)
            self.assertTrue(download.closed)
            self.assertTrue(get.call_args.kwargs.get("stream"))
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_cover_content_length_is_rejected_without_reading_body(self):
        download = StreamingResponse([b"a" * 8] * 10, {"Content-Length": "80"})
        with TemporaryDirectory() as root, \
                patch.object(covers, "COVERS_DIR", Path(root)), \
                patch.object(covers, "MAX_COVER_BYTES", 20), \
                patch.object(covers.requests, "get", return_value=download):
            self.assertIsNone(covers.download_cover("https://example.test/image", "test"))
            self.assertFalse(download.content_accessed)
            self.assertEqual(download.chunks_read, 0)
            self.assertTrue(download.closed)

    def test_concurrent_cover_downloads_use_separate_temporary_files(self):
        output = BytesIO()
        Image.new("RGB", (2, 2), "red").save(output, "JPEG")
        image_bytes = output.getvalue()
        barrier = Barrier(2)
        original_save = Image.Image.save
        temporary_paths = []

        def synchronized_save(image, path, *args, **kwargs):
            temporary_paths.append(str(path))
            original_save(image, path, *args, **kwargs)
            barrier.wait(timeout=5)

        with TemporaryDirectory() as root, \
                patch.object(covers, "COVERS_DIR", Path(root)), \
                patch.object(covers.requests, "get", side_effect=lambda *a, **k: StreamingResponse([image_bytes])), \
                patch.object(Image.Image, "save", synchronized_save), \
                ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(
                covers.download_cover, "https://example.test/image", "same-id", force=True,
            ) for _ in range(2)]
            results = [future.result(timeout=10) for future in futures]
            self.assertTrue(all(results))
            self.assertEqual(len(set(temporary_paths)), 2)
            self.assertEqual(list(Path(root).iterdir()), [Path(results[0])])

    def test_failed_cover_encoding_removes_temporary_file_and_preserves_cache(self):
        output = BytesIO()
        Image.new("RGB", (2, 2), "red").save(output, "JPEG")
        image_bytes = output.getvalue()

        def broken_save(image, path, *args, **kwargs):
            Path(path).write_bytes(b"partial-image")
            raise OSError("Synthetic encoder failure")

        with TemporaryDirectory() as root, \
                patch.object(covers, "COVERS_DIR", Path(root)), \
                patch.object(covers.requests, "get", return_value=StreamingResponse([image_bytes])), \
                patch.object(Image.Image, "save", broken_save):
            cache_path = Path(root) / "test.jpg"
            cache_path.write_bytes(image_bytes)
            self.assertIsNone(covers.download_cover("https://example.test/image", "test", force=True))
            self.assertEqual(cache_path.read_bytes(), image_bytes)
            self.assertEqual(list(Path(root).iterdir()), [cache_path])

    def test_retry_closes_discarded_stream_before_next_request(self):
        throttled = Mock(status_code=429, headers={"Retry-After": "0"})
        success = Mock(status_code=200)
        success.raise_for_status.return_value = None
        with patch("scrapers.http.time.sleep"):
            self.assertIs(get_with_retry(
                "https://example.test", requester=Mock(side_effect=[throttled, success]), stream=True,
            ), success)
        throttled.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
