from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AudioBook:
    file_path: str
    folder_path: str
    identifier: str = ""
    identifier_type: str = "unknown"  # "asin" | "isbn" | "unknown"

    # Metadata
    title: str = ""
    subtitle: str = ""
    author: str = ""
    narrator: str = ""
    series: str = ""
    series_number: str = ""
    description: str = ""
    publisher: str = ""
    year: str = ""
    genre: str = ""
    language: str = ""
    copyright_info: str = ""
    asin_tag: str = ""
    cdek_tag: str = ""

    # Cover
    cover_path: str | None = None
    has_embedded_cover: bool = False

    # State
    metadata_source: str = ""
    is_modified: bool = False
    _original_values: dict = field(default_factory=dict, repr=False)

    @property
    def filename(self) -> str:
        return Path(self.file_path).name

    @property
    def folder_name(self) -> str:
        return Path(self.folder_path).name

    @property
    def display_title(self) -> str:
        return self.title or self.filename

    def snapshot(self):
        """Save current values so we can detect changes later."""
        self._original_values = {
            "title": self.title,
            "subtitle": self.subtitle,
            "author": self.author,
            "narrator": self.narrator,
            "series": self.series,
            "series_number": self.series_number,
            "description": self.description,
            "publisher": self.publisher,
            "year": self.year,
            "genre": self.genre,
            "language": self.language,
            "copyright_info": self.copyright_info,
            "asin_tag": self.asin_tag,
            "cdek_tag": self.cdek_tag,
            "identifier": self.identifier,
            "identifier_type": self.identifier_type,
        }
        self.is_modified = False

    def check_modified(self):
        """Update is_modified by comparing to snapshot."""
        if not self._original_values:
            return
        for key, original in self._original_values.items():
            if getattr(self, key) != original:
                self.is_modified = True
                return
        self.is_modified = False

    def revert(self):
        """Revert to snapshot values."""
        if not self._original_values:
            return
        for key, val in self._original_values.items():
            setattr(self, key, val)
        self.is_modified = False


@dataclass
class MetadataResult:
    source: str  # "audible", "google_books", "openlibrary", "libation", "embedded"
    title: str = ""
    subtitle: str = ""
    author: str = ""
    narrator: str = ""
    series: str = ""
    series_number: str = ""
    description: str = ""
    publisher: str = ""
    year: str = ""
    genre: str = ""
    cover_url: str = ""
    language: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "author": self.author,
            "narrator": self.narrator,
            "series": self.series,
            "series_number": self.series_number,
            "description": self.description,
            "publisher": self.publisher,
            "year": self.year,
            "genre": self.genre,
            "cover_url": self.cover_url,
            "language": self.language,
        }

    def non_empty_fields(self) -> dict:
        d = self.to_dict()
        return {k: v for k, v in d.items() if v}
