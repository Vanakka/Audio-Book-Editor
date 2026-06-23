"""Scrape audiobook metadata from Goodreads search results."""

import re
import time

import requests
from bs4 import BeautifulSoup

from core.models import MetadataResult
from scrapers.base import BaseScraper
from scrapers.http import RETRY_STATUSES, get_with_retry
from scrapers.matching import is_relevant

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

SEARCH_URL = "https://www.goodreads.com/search"


class GoodreadsScraper(BaseScraper):
    def __init__(self, delay: float = 1.5):
        self._session = requests.Session()
        self._session.headers.update(HEADERS)
        self._delay = delay
        self._last_request = 0.0

    def name(self) -> str:
        return "Goodreads"

    def supports_identifier_type(self, id_type: str) -> bool:
        return True  # Can search by title/author for any type

    def fetch(self, identifier: str, identifier_type: str = "asin",
              title_hint: str = "", author_hint: str = "") -> MetadataResult | None:
        if not title_hint:
            return None

        self._rate_limit()

        # Search by title + author
        query = title_hint
        if author_hint:
            # Use first author name only
            first_author = author_hint.split(",")[0].strip()
            query = f"{title_hint} {first_author}"

        try:
            resp = get_with_retry(
                SEARCH_URL, requester=self._session.get,
                params={"q": query}, timeout=15,
                retry_statuses=RETRY_STATUSES | {202},
            )
        except requests.RequestException as e:
            raise RuntimeError(f"Goodreads request failed: {e}") from e

        # Parse search results and get the first book's page
        soup = BeautifulSoup(resp.text, "html.parser")
        first_link = None
        for link in soup.select("a.bookTitle"):
            row = link.find_parent("tr")
            author_el = row.select_one("a.authorName span") if row else None
            candidate_author = author_el.get_text(strip=True) if author_el else ""
            if is_relevant(link.get_text(strip=True), title_hint, candidate_author, author_hint):
                first_link = link
                break
        if not first_link:
            return None

        book_url = first_link.get("href", "")
        if not book_url.startswith("http"):
            book_url = f"https://www.goodreads.com{book_url}"

        # Fetch the book page
        self._rate_limit()
        try:
            resp = get_with_retry(
                book_url, requester=self._session.get, timeout=15,
                retry_statuses=RETRY_STATUSES | {202},
            )
        except requests.RequestException as e:
            raise RuntimeError(f"Goodreads book request failed: {e}") from e

        return self._parse_book_page(resp.text)

    def _rate_limit(self):
        elapsed = time.time() - self._last_request
        if elapsed < self._delay:
            time.sleep(self._delay - elapsed)
        self._last_request = time.time()

    def _parse_book_page(self, html: str) -> MetadataResult | None:
        soup = BeautifulSoup(html, "html.parser")
        result = MetadataResult(source="goodreads")

        # Title
        title_el = soup.select_one("h1[data-testid='bookTitle']") or soup.select_one("h1#bookTitle") or soup.select_one("h1")
        if title_el:
            result.title = title_el.get_text(strip=True)

        # Author
        author_el = soup.select_one("span.ContributorLink__name") or soup.select_one("a.authorName span")
        if author_el:
            result.author = author_el.get_text(strip=True)

        # Description
        desc_el = soup.select_one("div[data-testid='description'] span.Formatted") or soup.select_one("div#description span")
        if desc_el:
            result.description = desc_el.get_text(strip=True)

        # Cover image
        cover_el = soup.select_one("img.ResponsiveImage") or soup.select_one("img#coverImage")
        if cover_el:
            src = cover_el.get("src", "")
            if src:
                result.cover_url = src

        # Genre/Shelves
        genre_els = soup.select("span.BookPageMetadataSection__genreButton a span")
        if not genre_els:
            genre_els = soup.select("a.actionLinkLite.bookPageGenreLink")
        if genre_els:
            genres = [g.get_text(strip=True) for g in genre_els[:4]]
            result.genre = ", ".join(genres)

        # Series info from title
        series_el = soup.select_one("h3.Text__italic a") or soup.select_one("div#bookSeries a")
        if series_el:
            series_text = series_el.get_text(strip=True)
            # Parse "Series Name #3" format
            m = re.match(r'(.+?)\s*#(\d+(?:\.\d+)?)', series_text)
            if m:
                result.series = m.group(1).strip()
                result.series_number = m.group(2)
            else:
                result.series = series_text

        # Year from publication info
        pub_el = soup.select_one("p[data-testid='publicationInfo']") or soup.select_one("div#details div.row")
        if pub_el:
            text = pub_el.get_text()
            year_match = re.search(r'(\d{4})', text)
            if year_match:
                result.year = year_match.group(1)

        # Publisher
        if pub_el:
            text = pub_el.get_text()
            pub_match = re.search(r'by\s+(.+?)(?:\.|$)', text)
            if pub_match:
                result.publisher = pub_match.group(1).strip()

        return result if result.title else None
