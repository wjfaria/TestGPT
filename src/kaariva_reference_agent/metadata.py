from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader


def extract_title(path: Path, fallback: str) -> str:
    if path.suffix.lower() == ".pdf":
        try:
            pdf = PdfReader(str(path))
            if pdf.metadata and pdf.metadata.title:
                return str(pdf.metadata.title)
        except Exception:
            return fallback
    if path.suffix.lower() in {".html", ".htm"}:
        soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
        if soup.title and soup.title.string:
            return soup.title.string.strip()
    return fallback
