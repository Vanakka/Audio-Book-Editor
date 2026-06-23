"""Safe, stable filenames for application cache entries."""

import hashlib
import re


SAFE_CACHE_KEY = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


def safe_cache_key(identifier: str = "", fallback: str = "") -> str:
    """Return a path-safe identifier, hashing untrusted or empty values."""
    identifier = (identifier or "").strip()
    if identifier not in ("", ".", "..") and SAFE_CACHE_KEY.fullmatch(identifier):
        return identifier

    source = identifier or fallback or "anonymous"
    return hashlib.sha256(source.encode("utf-8", errors="replace")).hexdigest()[:24]
