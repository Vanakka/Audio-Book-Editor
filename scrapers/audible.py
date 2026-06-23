"""Scrape audiobook metadata from Audible product pages."""

import re
import time

import requests
from bs4 import BeautifulSoup

from core.models import MetadataResult
from scrapers.base import BaseScraper
from scrapers.http import get_with_retry

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class AudibleScraper(BaseScraper):
    def __init__(self, delay: float = 1.5):
        self._session = requests.Session()
        self._session.headers.update(HEADERS)
        self._delay = delay
        self._last_request = 0.0

    def name(self) -> str:
        return "Audible"

    def supports_identifier_type(self, id_type: str) -> bool:
        return id_type == "asin"

    def fetch(self, identifier: str, identifier_type: str = "asin",
              title_hint: str = "", author_hint: str = "") -> MetadataResult | None:
        if identifier_type != "asin":
            return None

        self._rate_limit()

        url = f"https://www.audible.com/pd/{identifier}"
        try:
            resp = get_with_retry(
                url, requester=self._session.get,
                timeout=15, allow_redirects=True,
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Audible request failed for {identifier}: {e}") from e

        return self._parse_page(resp.text, identifier)

    def _rate_limit(self):
        elapsed = time.time() - self._last_request
        if elapsed < self._delay:
            time.sleep(self._delay - elapsed)
        self._last_request = time.time()

    def _parse_page(self, html: str, asin: str) -> MetadataResult | None:
        soup = BeautifulSoup(html, "html.parser")
        result = MetadataResult(source="audible")

        # Title
        title_el = soup.select_one("h1.bc-heading") or soup.select_one("h1")
        if title_el:
            result.title = title_el.get_text(strip=True)

        # Author
        author_el = soup.select_one("li.authorLabel a") or soup.select_one(".authorLabel a")
        if author_el:
            result.author = author_el.get_text(strip=True)
        else:
            # Try alternative selectors
            for a in soup.select("a"):
                href = a.get("href", "")
                if "/author/" in href:
                    result.author = a.get_text(strip=True)
                    break

        # Narrator
        narrator_el = soup.select_one("li.narratorLabel a") or soup.select_one(".narratorLabel a")
        if narrator_el:
            result.narrator = narrator_el.get_text(strip=True)

        # Series
        series_el = soup.select_one("li.seriesLabel a") or soup.select_one(".seriesLabel a")
        if series_el:
            series_text = series_el.get_text(strip=True)
            result.series = series_text
            # Try to extract book number from surrounding text
            series_li = series_el.parent
            if series_li:
                full_text = series_li.get_text()
                num_match = re.search(r'Book\s+(\d+(?:\.\d+)?)', full_text)
                if num_match:
                    result.series_number = num_match.group(1)

        # Description
        desc_el = soup.select_one("div.productPublisherSummary span") or soup.select_one(".productPublisherSummary")
        if desc_el:
            result.description = desc_el.get_text(strip=True)

        # Cover image
        for img in soup.select("img"):
            src = img.get("src", "")
            if "images-na.ssl-images-amazon.com" in src or "m.media-amazon.com" in src:
                if "SX" in src or "SL" in src:
                    # Get largest version
                    result.cover_url = re.sub(r'\._[^.]+_\.', '._SL2400_.', src)
                    break

        # Publisher and release date from product details
        for li in soup.select("li.bc-list-item"):
            text = li.get_text()
            if "Publisher:" in text:
                result.publisher = text.replace("Publisher:", "").strip()
            elif "Release date:" in text or "Release Date:" in text:
                date_text = re.sub(r'Release [Dd]ate:\s*', '', text).strip()
                year_match = re.search(r'(\d{4})', date_text)
                if year_match:
                    result.year = year_match.group(1)

        # Genre from breadcrumbs
        breadcrumbs = soup.select("li.bc-chip a, .categoriesLabel a")
        if breadcrumbs:
            genres = [b.get_text(strip=True) for b in breadcrumbs[:3]]
            result.genre = ", ".join(genres)

        return result if result.title else None
