"""Small HTTP retry helper shared by metadata providers."""

import time
from collections.abc import Callable

import requests


RETRY_STATUSES = {429, 500, 502, 503, 504}


def get_with_retry(url: str, *, requester: Callable = requests.get,
                   attempts: int = 3, backoff: float = 0.5,
                   retry_statuses: set[int] | None = None, **kwargs):
    """GET a URL with bounded exponential retry for transient responses."""
    statuses = RETRY_STATUSES if retry_statuses is None else retry_statuses
    last_response = None

    for attempt in range(max(1, attempts)):
        response = requester(url, **kwargs)
        last_response = response
        if response.status_code not in statuses:
            try:
                response.raise_for_status()
            except requests.RequestException:
                response.close()
                raise
            return response

        # A rejected streamed response otherwise keeps its connection open.
        response.close()
        if attempt + 1 < attempts:
            retry_after = response.headers.get("Retry-After", "")
            try:
                delay = min(float(retry_after), 10.0) if retry_after else backoff * (2 ** attempt)
            except ValueError:
                delay = backoff * (2 ** attempt)
            time.sleep(max(0.0, delay))

    last_response.raise_for_status()
    raise requests.HTTPError(
        f"Transient HTTP status {last_response.status_code} after {attempts} attempts",
        response=last_response,
    )
