"""Conservative relevance checks for title/author search results."""

import re
import unicodedata
from difflib import SequenceMatcher


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, _normalize(left), _normalize(right)).ratio()


def is_relevant(candidate_title: str, title_hint: str,
                candidate_author: str = "", author_hint: str = "") -> bool:
    """Return whether a catalog result is similar enough for automatic use."""
    candidate = _normalize(candidate_title)
    expected = _normalize(title_hint)
    if not candidate or not expected:
        return bool(candidate)

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
