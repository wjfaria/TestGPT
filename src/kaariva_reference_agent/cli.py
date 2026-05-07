from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

import typer

from .allowlist import Allowlist
from .classifier import Classifier
from .downloader import download_document
from .license_gate import infer_license_status
from .manifest import MANIFEST_PATH, REVIEW_PATH, write_manifest
from .schemas import ManifestRecord, SeedRecord
from .storage import build_local_path
from .utils import sha256_file

app = typer.Typer()


def read_seeds(csv_path: Path) -> list[SeedRecord]:
    with csv_path.open("r", encoding="utf-8") as f:
        return [SeedRecord.model_validate(row) for row in csv.DictReader(f)]


@app.command("init")
def init_project() -> None:
    for path in [MANIFEST_PATH, REVIEW_PATH, Path("data/manifest/rejected_documents.jsonl")]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
    typer.echo("Initialized manifest files")


@app.command("validate-seeds")
def validate_seeds(csv_file: Path) -> None:
    seeds = read_seeds(csv_file)
    typer.echo(f"Validated {len(seeds)} seed rows")


@app.command("process-seeds")
def process_seeds(csv_file: Path) -> None:
    seeds = read_seeds(csv_file)
    allowlist = Allowlist()
    classifier = Classifier()
    for idx, seed in enumerate(seeds, start=1):
        allowed = allowlist.is_allowed(str(seed.source_url))
        classification = classifier.classify(seed.title, seed.notes)
        ext = "pdf" if str(seed.source_url).lower().endswith(".pdf") else "html"
        local_path = build_local_path(classification, seed.title, ext)
        access_status = "public" if allowed else "rejected"
        download_allowed = allowed
        checksum = ""
        file_format = "metadata"
        if download_allowed:
            ok, _ = download_document(str(seed.source_url), local_path)
            if ok:
                checksum = sha256_file(local_path)
                file_format = "pdf" if ext == "pdf" else "html"
            else:
                access_status = "metadata_only"
                local_path = Path("documents/99_human_review_required") / f"seed_{idx}.metadata"
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_text(json.dumps(seed.model_dump(mode='json')), encoding="utf-8")
                checksum = sha256_file(local_path)
                file_format = "metadata"
        license_status = infer_license_status(f"{seed.expected_issuer} {seed.notes} {seed.title}")
        human_review = (not allowed) or classification == "99_human_review_required" or license_status in {
            "manual_review_required",
            "publisher_restricted",
        }
        record = ManifestRecord(
            document_id=f"KAARIVA-SEED-{idx:03d}",
            title=seed.title,
            issuer=seed.expected_issuer,
            jurisdiction=seed.jurisdiction,
            document_type="Guidance or reference",
            topic_tags=[seed.expected_category],
            source_url=seed.source_url,
            access_status=access_status,
            license_status=license_status,
            download_allowed=download_allowed,
            retrieved_date=date.today(),
            file_format=file_format,
            local_path=str(local_path),
            checksum_sha256=checksum,
            classification=classification,
            relevance_to_kaariva="Seeded document for governed intake.",
            use_in_rag=download_allowed and not human_review,
            human_review_required=human_review,
        )
        write_manifest(record)
    typer.echo(f"Processed {len(seeds)} seeds")


@app.command("classify-file")
def classify_file(path: Path) -> None:
    classifier = Classifier()
    typer.echo(classifier.classify(path.name))


@app.command("show-manifest")
def show_manifest() -> None:
    if not MANIFEST_PATH.exists():
        typer.echo("Manifest not found")
        return
    typer.echo(MANIFEST_PATH.read_text(encoding="utf-8"))


@app.command("export-review-queue")
def export_review_queue() -> None:
    if REVIEW_PATH.exists():
        typer.echo(REVIEW_PATH.read_text(encoding="utf-8"))
