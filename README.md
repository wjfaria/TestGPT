# KAARIVA Reference Agent MVP (0.1)

Governed document intake support for KAARIVA research infrastructure workflows.

## What this MVP does
- Validates seed URLs from CSV.
- Enforces an allowlist before attempting download.
- Downloads only public HTML/PDF content from allowlisted sources.
- Creates document manifest records in JSONL.
- Routes uncertain/restricted items to human review.

## Governance rules
- No paywall bypassing.
- No pirate or shadow library sources.
- Unknown licensing/access is routed for review.
- This tool supports document intake operations and does not provide legal, clinical, or regulatory advice.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## CLI
```bash
kaariva-ref init
kaariva-ref validate-seeds data/seed_sources.csv
kaariva-ref process-seeds data/seed_sources.csv
kaariva-ref classify-file documents/sample.pdf
kaariva-ref show-manifest
kaariva-ref export-review-queue
```

## Data outputs
- `data/manifest/document_manifest.jsonl`
- `data/manifest/human_review_queue.jsonl`
- `data/manifest/rejected_documents.jsonl`

## Next steps
- Add richer metadata extraction (issuer, version date, jurisdiction detection).
- Add explicit paywall detection heuristics.
- Add optional SQLite index for workflow dashboards.
- Add manual URL approval workflow and provenance signatures.
