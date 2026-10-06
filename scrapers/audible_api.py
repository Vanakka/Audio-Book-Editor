"""Fetch audiobook metadata from the Audible catalog API."""

import re

import requests

from core.models import MetadataResult
from scrapers.base import BaseScraper
from scrapers.http import get_with_retry

API_URL = "https://api.audible.com/1.0/catalog/products"
RESPONSE_GROUPS = "product_desc,contributors,series,product_attrs,media,rating,category_ladders"
SEARCH_RESPONSE_GROUPS = "product_desc,contributors,series"
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}


def _search_title_candidates(title: str) -> list[str]:
    """Return the full title followed by a likely title without its subtitle."""
    title = title.strip()
    if not title:
        return []

    candidates = [title]
    primary_title = re.split(r":\s*|\s+(?:-|–|—)\s+", title, maxsplit=1)[0].strip()
    if primary_title and primary_title != title:
        candidates.append(primary_title)
    return candidates


def search_catalog(title: str, author: str = "", num_results: int = 10,
                   response_groups: str = SEARCH_RESPONSE_GROUPS) -> list[dict]:
    """Search Audible, relaxing subtitle and author filters when necessary."""
    author = author.split(",", 1)[0].strip()

    for title_candidate in _search_title_candidates(title):
        author_candidates = [author, ""] if author else [""]
        for author_candidate in author_candidates:
            params = {
                "title": title_candidate,
                "response_groups": response_groups,
                "num_results": num_results,
            }
            if author_candidate:
                params["author"] = author_candidate

            resp = get_with_retry(
                API_URL,
                requester=requests.get,
                params=params,
                headers=REQUEST_HEADERS,
                timeout=10,
            )
            resp.raise_for_status()
            products = resp.json().get("products", [])
            if products:
                return products

    return []


class AudibleAPIScraper(BaseScraper):
    def name(self) -> str:
        return "Audible API"

    def supports_identifier_type(self, id_type: str) -> bool:
        return id_type == "asin"

    def fetch(self, identifier: str, identifier_type: str = "asin",
              title_hint: str = "", author_hint: str = "") -> MetadataResult | None:
        if identifier_type != "asin":
            return None

        url = f"{API_URL}/{identifier}"
        params = {"response_groups": RESPONSE_GROUPS}
        try:
            resp = get_with_retry(
                url, requester=requests.get, params=params,
                headers=REQUEST_HEADERS, timeout=15,
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as e:
            if isinstance(e, requests.RequestException) and e.response is not None and e.response.status_code == 404:
                return None
            raise RuntimeError(
                f"Audible API request failed for {identifier}: {e}"
            ) from e

        product = data.get("product")
        if not product:
            return None

        return self._parse_product(product)

    def _parse_product(self, prod: dict) -> MetadataResult | None:
        if not prod.get("title"):
            return None
        result = MetadataResult(source="audible_api")

        result.title = prod.get("title", "")
        result.subtitle = prod.get("subtitle", "")
        result.publisher = prod.get("publisher_name", "")
        result.language = prod.get("language", "")

        # Authors
        authors = prod.get("authors", [])
        if authors:
            result.author = ", ".join(a.get("name", "") for a in authors)

        # Narrators
        narrators = prod.get("narrators", [])
        if narrators:
            result.narrator = ", ".join(n.get("name", "") for n in narrators)

        # Series
        series_list = prod.get("series", [])
        if series_list:
            first_series = series_list[0]
            result.series = first_series.get("title", "")
            result.series_number = first_series.get("sequence", "")

        # Year from release date
        release_date = prod.get("release_date", "")
        if release_date:
            result.year = release_date[:4]

        # Description
        desc = prod.get("publisher_summary", "") or prod.get("merchandising_summary", "")
        if desc:
            # Strip HTML tags
            import re
            desc = re.sub(r'<br\s*/?>', '\n', desc, flags=re.IGNORECASE)
            desc = re.sub(r'<[^>]+>', '', desc)
            desc = re.sub(r'\n{3,}', '\n\n', desc)
            result.description = desc.strip()

        # Genre from category ladders
        categories = prod.get("category_ladders", [])
        genres = []
        for ladder in categories:
            for cat in ladder.get("ladder", []):
                name = cat.get("name", "")
                if name and name not in genres:
                    genres.append(name)
        if genres:
            result.genre = ", ".join(genres[:4])

        # Cover image - get largest available
        images = prod.get("product_images", {})
        for size in ("2400", "1024", "500", "252"):
            if size in images:
                result.cover_url = images[size]
                break

        return result
