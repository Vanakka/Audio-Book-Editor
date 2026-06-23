"""Abstract base class for metadata scrapers."""

from abc import ABC, abstractmethod
from core.models import MetadataResult


class BaseScraper(ABC):
    @abstractmethod
    def fetch(self, identifier: str, identifier_type: str = "asin",
              title_hint: str = "", author_hint: str = "") -> MetadataResult | None:
        """Fetch metadata for an audiobook. Returns None if not found."""
        ...

    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the scraper."""
        ...

    @abstractmethod
    def supports_identifier_type(self, id_type: str) -> bool:
        """Whether this scraper can use the given identifier type."""
        ...
