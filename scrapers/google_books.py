"""Fetch audiobook metadata from Google Books API."""

import requests

from core.models import MetadataResult
from scrapers.base import BaseScraper
from scrapers.http import get_with_retry
from scrapers.matching import is_relevant

API_URL = "https://www.googleapis.com/books/v1/volumes"


class GoogleBooksScraper(BaseScraper):
    def name(self) -> str:
        return "Google Books"

    def supports_identifier_type(self, id_type: str) -> bool:
        return True  # Can search by title/author for any type

    def fetch(self, identifier: str, identifier_type: str = "asin",
              title_hint: str = "", author_hint: str = "") -> MetadataResult | None:
        # Build query
        if identifier_type == "isbn":
            query = f"isbn:{identifier}"
        elif title_hint:
            query = f"intitle:{title_hint}"
            if author_hint:
                query += f"+inauthor:{author_hint}"
        else:
            return None

        try:
            resp = get_with_retry(
                API_URL, requester=requests.get,
                params={"q": query, "maxResults": 5}, timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as e:
            raise RuntimeError(f"Google Books request failed: {e}") from e

        if data.get("totalItems", 0) == 0:
            return None

        # Find best match
        for item in data.get("items", []):
            vol = item.get("volumeInfo", {})
            candidate_authors = ", ".join(vol.get("authors", []))
            if title_hint and not is_relevant(
                vol.get("title", ""), title_hint, candidate_authors, author_hint
            ):
                continue
            result = self._parse_volume(vol)
            if result:
                return result

        return None

    def _parse_volume(self, vol: dict) -> MetadataResult | None:
        title = vol.get("title", "")
        if not title:
            return None

        result = MetadataResult(source="google_books")
        result.title = title
        result.subtitle = vol.get("subtitle", "")
        result.author = ", ".join(vol.get("authors", []))
        result.publisher = vol.get("publisher", "")
        result.description = vol.get("description", "")
        result.language = vol.get("language", "")

        # Year from publishedDate
        pub_date = vol.get("publishedDate", "")
        if pub_date:
            result.year = pub_date[:4]

        # Genre from categories
        categories = vol.get("categories", [])
        if categories:
            result.genre = ", ".join(categories)

        # Cover image
        images = vol.get("imageLinks", {})
        # Prefer larger images
        for key in ("extraLarge", "large", "medium", "small", "thumbnail"):
            if key in images:
                url = images[key]
                # Remove zoom parameter for larger image
                url = url.replace("&edge=curl", "")
                result.cover_url = url
                break

        return result
