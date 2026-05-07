from __future__ import annotations

import json
from pathlib import Path

from .schemas import ManifestRecord


MANIFEST_PATH = Path("data/manifest/document_manifest.jsonl")
REVIEW_PATH = Path("data/manifest/human_review_queue.jsonl")
REJECTED_PATH = Path("data/manifest/rejected_documents.jsonl")


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


def write_manifest(record: ManifestRecord) -> None:
    data = record.model_dump(mode="json")
    append_jsonl(MANIFEST_PATH, data)
    if record.human_review_required:
        append_jsonl(REVIEW_PATH, data)
    if record.access_status == "rejected":
        append_jsonl(REJECTED_PATH, data)
