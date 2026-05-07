from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from urllib.parse import urlparse


class ValidationError(ValueError):
    """Basic validation error for lightweight schema fallback."""


def _validate_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValidationError(f"Invalid URL: {value}")
    return value


@dataclass
class SeedRecord:
    title: str
    source_url: str
    expected_issuer: str
    expected_category: str
    jurisdiction: str
    notes: str = ""
    priority: str = "medium"

    def __post_init__(self) -> None:
        self.source_url = _validate_url(self.source_url)

    @classmethod
    def model_validate(cls, row: dict) -> "SeedRecord":
        return cls(**row)

    def model_dump(self, mode: str = "python") -> dict:
        return asdict(self)


@dataclass
class ManifestRecord:
    document_id: str
    title: str
    issuer: str
    jurisdiction: str
    document_type: str
    topic_tags: list[str] = field(default_factory=list)
    disease_area: str = "general"
    source_url: str = ""
    access_status: str = "unknown"
    license_status: str = "manual_review_required"
    download_allowed: bool = False
    version_date: str = "unknown"
    retrieved_date: date = field(default_factory=date.today)
    file_format: str = "metadata"
    local_path: str = ""
    checksum_sha256: str = ""
    classification: str = "99_human_review_required"
    relevance_to_kaariva: str = ""
    use_in_rag: bool = False
    human_review_required: bool = True
    review_status: str = "pending"

    def __post_init__(self) -> None:
        self.source_url = _validate_url(self.source_url)

    def model_dump(self, mode: str = "python") -> dict:
        data = asdict(self)
        if mode == "json":
            data["retrieved_date"] = self.retrieved_date.isoformat()
        return data
