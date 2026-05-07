from __future__ import annotations

from pathlib import Path


def safe_filename(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")[:80]


def build_local_path(classification: str, title: str, ext: str) -> Path:
    return Path("documents") / classification / f"{safe_filename(title)}.{ext}"
