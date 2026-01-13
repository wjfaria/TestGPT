from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class TrialSummary:
    trial_id: str
    title: str
    condition: str
    url: str


@dataclass(frozen=True)
class TrialDocument:
    title: str
    url: str
    filename: str
    doc_type: str | None = None


@dataclass(frozen=True)
class DownloadedDocument:
    title: str
    url: str
    filename: str
    sha256: str
    downloaded_at: str
    doc_type: str | None = None


@dataclass(frozen=True)
class TrialMetadata:
    trial_id: str
    title: str
    condition: str
    url: str
    documents: Iterable[DownloadedDocument]
