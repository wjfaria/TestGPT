from __future__ import annotations

from pathlib import Path


def _load_categories(path: Path) -> list[dict]:
    categories: list[dict] = []
    current: dict | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("- code:"):
            if current:
                categories.append(current)
            current = {"code": line.split(":", 1)[1].strip().strip('"'), "keywords": []}
        elif line.startswith("keywords:") and current is not None:
            val = line.split(":", 1)[1].strip().strip("[]")
            current["keywords"] = [x.strip().strip('"') for x in val.split(",") if x.strip()]
    if current:
        categories.append(current)
    return categories


class Classifier:
    def __init__(self, taxonomy_path: str = "config/document_taxonomy.yaml") -> None:
        self.categories = _load_categories(Path(taxonomy_path))

    def classify(self, title: str, notes: str = "") -> str:
        blob = f"{title} {notes}".lower()
        for category in self.categories:
            if any(keyword.lower() in blob for keyword in category.get("keywords", [])):
                return category["code"]
        return "99_human_review_required"
