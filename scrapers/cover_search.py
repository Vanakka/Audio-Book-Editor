"""Provider-neutral cover search functions suitable for worker threads."""

import re

import requests
from bs4 import BeautifulSoup

from scrapers.audible_api import API_URL, REQUEST_HEADERS, search_catalog
from scrapers.http import RETRY_STATUSES, get_with_retry


def search_audible_covers(query: str, author: str = "") -> list[dict]:
    # Ordinary ten-letter titles (e.g. Foundation) are not catalog IDs.
    if re.fullmatch(r"(?:B[0-9][A-Za-z0-9]{8}|[0-9]{9}[0-9X])", query, re.IGNORECASE):
        response = get_with_retry(
            f"{API_URL}/{query.upper()}", requester=requests.get,
            params={"response_groups": "product_desc,media"},
            headers=REQUEST_HEADERS, timeout=10,
        )
        data = response.json()
        products = [data["product"]] if data.get("product") else []
    else:
        products = search_catalog(
            query, author, num_results=5,
            response_groups="product_desc,contributors,series,media",
        )

    results = []
    for product in products:
        images = product.get("product_images", {})
        cover_url = images.get("2400") or images.get("1024") or images.get("500", "")
        if cover_url:
            results.append({
                "title": product.get("title", "Unknown title"),
                "asin": product.get("asin", ""),
                "cover_url": cover_url,
            })
    return results


def search_goodreads_covers(query: str, author: str = "") -> list[dict]:
    search_query = f"{query} {author}".strip()
    response = get_with_retry(
        "https://www.goodreads.com/search", requester=requests.get,
        params={"q": search_query}, headers={"User-Agent": "Mozilla/5.0"}, timeout=15,
        retry_statuses=RETRY_STATUSES | {202},
    )
    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for link in soup.select("a.bookTitle")[:5]:
        row = link.find_parent("tr")
        image = (row.select_one("img.bookCover") or row.select_one("img")) if row else None
        if not image:
            continue
        thumbnail = image.get("src", "")
        cover_url = re.sub(r"\._[^.]+_\.", ".", thumbnail)
        if cover_url:
            results.append({"title": link.get_text(strip=True), "asin": "", "cover_url": cover_url})
    return results
