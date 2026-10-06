"""Conservative relevance checks for title/author search results."""

import re
import unicodedata
from decimal import Decimal
from difflib import SequenceMatcher


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.findall(r"[^\W_]+", value.casefold()))


def _volume_number(value: str) -> Decimal | None:
    """Identify explicit volume markers or a number ending the primary title."""
    value = unicodedata.normalize("NFKC", value or "")
    primary = re.split(r":\s*|\s+(?:-|–|—)\s+", value, maxsplit=1)[0].strip()
    explicit = re.search(
        r"(?:\b(?:book|volume|vol\.?)\s*|#\s*)(\d+(?:\.\d+)?)\b",
        primary, re.IGNORECASE,
    )
    # Bare four-digit numbers are commonly publication years, not volumes.
    trailing = re.search(r"\b(\d{1,3}(?:\.\d+)?)$", primary)
    match = explicit or trailing
    return Decimal(match.group(1)) if match else None


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, _normalize(left), _normalize(right)).ratio()


def is_relevant(candidate_title: str, title_hint: str,
                candidate_author: str = "", author_hint: str = "") -> bool:
    """Return whether a catalog result is similar enough for automatic use."""
    candidate = _normalize(candidate_title)
    expected = _normalize(title_hint)
    if not candidate or not expected:
        return bool(candidate)

    candidate_volume = _volume_number(candidate_title)
    expected_volume = _volume_number(title_hint)
    if candidate_volume is not None and expected_volume is not None and candidate_volume != expected_volume:
        return False

    candidate_tokens = set(candidate.split())
    expected_tokens = set(expected.split())
    overlap = len(candidate_tokens & expected_tokens) / max(len(candidate_tokens), len(expected_tokens), 1)
    title_match = (
        candidate in expected or expected in candidate
        or _similarity(candidate, expected) >= 0.68
        or overlap >= 0.60
    )
    if not title_match:
        return False

    if candidate_author and author_hint:
        cand_author = _normalize(candidate_author)
        expected_author = _normalize(author_hint.split(",", 1)[0])
        cand_parts = cand_author.split()
        expected_parts = expected_author.split()
        surname_match = bool(cand_parts and expected_parts and _similarity(cand_parts[-1], expected_parts[-1]) >= 0.80)
        if _similarity(cand_author, expected_author) < 0.60 and not surname_match:
            return False

    return True
