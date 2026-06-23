"""Fetch audiobook metadata from OpenLibrary API."""

import requests

from core.models import MetadataResult
from scrapers.base import BaseScraper
from scrapers.http import get_with_retry
from scrapers.matching import is_relevant

SEARCH_URL = "https://openlibrary.org/search.json"


class OpenLibraryScraper(BaseScraper):
    def name(self) -> str:
        return "OpenLibrary"

    def supports_identifier_type(self, id_type: str) -> bool:
        return True

    def fetch(self, identifier: str, identifier_type: str = "asin",
              title_hint: str = "", author_hint: str = "") -> MetadataResult | None:
        params = {}
        if identifier_type == "isbn":
            params["isbn"] = identifier
        elif title_hint:
            params["title"] = title_hint
            if author_hint:
                params["author"] = author_hint
        else:
            return None

        params["limit"] = 5

        try:
            resp = get_with_retry(
                SEARCH_URL, requester=requests.get, params=params, timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as e:
            raise RuntimeError(f"OpenLibrary request failed: {e}") from e

        docs = data.get("docs", [])
        if not docs:
            return None

        for doc in docs:
            candidate_authors = ", ".join(doc.get("author_name", []))
            if title_hint and not is_relevant(
                doc.get("title", ""), title_hint, candidate_authors, author_hint
            ):
                continue
            return self._parse_doc(doc)
        return None

    def _parse_doc(self, doc: dict) -> MetadataResult | None:
        title = doc.get("title", "")
        if not title:
            return None

        result = MetadataResult(source="openlibrary")
        result.title = title
        result.subtitle = doc.get("subtitle", "")
        result.author = ", ".join(doc.get("author_name", []))
        result.publisher = ", ".join(doc.get("publisher", [])[:2])

        # Year
        year = doc.get("first_publish_year")
        if year:
            result.year = str(year)

        # Genre/Subject
        subjects = doc.get("subject", [])
        if subjects:
            result.genre = ", ".join(subjects[:3])

        result.language = ", ".join(doc.get("language", [])[:2])

        # Cover
        cover_id = doc.get("cover_i")
        if cover_id:
            result.cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"

        return result
