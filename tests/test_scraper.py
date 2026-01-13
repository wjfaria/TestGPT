from __future__ import annotations

from pathlib import Path

from ctis_cli.scraper import (
    CTISScraper,
    parse_search_results,
    parse_search_results_json,
    parse_trial_documents,
)


SAMPLE_SEARCH_HTML = """
<div class="trial" data-trial-id="CT-2024-0001" data-condition="Oncology">
  <a href="/trial/CT-2024-0001">Study of oncology</a>
</div>
"""

SAMPLE_SEARCH_FALLBACK_HTML = """
<div class="results">
  <a href="/trial/CT-2024-0002">Fallback trial</a>
</div>
"""

SAMPLE_TRIAL_HTML = """
<div class="documents">
  <a class="document-download" href="/documents/protocol.pdf" data-doc-type="protocol">Protocol PDF</a>
  <a href="/documents/consent.pdf">Consent Form</a>
</div>
"""

SAMPLE_SEARCH_JSON = """
{
    "pagination": {
        "totalRecords": 1,
        "currentPage": 1
    },
    "data": [
        {
            "ctNumber": "2025-522955-25-00",
            "ctTitle": "Next Generation StaR TREC",
            "conditions": "Rectal cancer"
        }
    ]
}
"""


class FakeResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code
        self.ok = status_code < 400

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("HTTP error")


def test_parse_search_results() -> None:
    results = parse_search_results(SAMPLE_SEARCH_HTML, "https://example.com")
    assert len(results) == 1
    trial = results[0]
    assert trial.trial_id == "CT-2024-0001"
    assert trial.condition == "Oncology"
    assert trial.url == "https://example.com/trial/CT-2024-0001"


def test_parse_search_results_fallback() -> None:
    results = parse_search_results(SAMPLE_SEARCH_FALLBACK_HTML, "https://example.com")
    assert len(results) == 1
    trial = results[0]
    assert trial.trial_id == "CT-2024-0002"
    assert trial.title == "Fallback trial"
    assert trial.url == "https://example.com/trial/CT-2024-0002"


def test_parse_search_results_json() -> None:
    results = parse_search_results_json(SAMPLE_SEARCH_JSON, "https://example.com")
    assert results is not None
    assert len(results) == 1
    trial = results[0]
    assert trial.trial_id == "2025-522955-25-00"
    assert trial.title == "Next Generation StaR TREC"
    assert trial.condition == "Rectal cancer"
    assert trial.url == "https://example.com/trial/2025-522955-25-00"


def test_parse_trial_documents() -> None:
    docs = parse_trial_documents(SAMPLE_TRIAL_HTML, "https://example.com/trial/CT-2024-0001")
    assert len(docs) == 2
    assert docs[0].filename == "protocol.pdf"
    assert docs[0].doc_type == "protocol"
    assert docs[1].filename == "consent.pdf"


def test_download_documents(monkeypatch, tmp_path: Path) -> None:
    scraper = CTISScraper(base_url="https://example.com", user_agent="test-agent")

    def fake_get(url: str, **_kwargs):
        if url.endswith("robots.txt"):
            return FakeResponse("User-agent: *\nDisallow:")
        if "search" in url:
            return FakeResponse(SAMPLE_SEARCH_HTML)
        return FakeResponse(SAMPLE_TRIAL_HTML)

    def fake_stream(url: str, **_kwargs):
        return [b"pdf-content"]

    monkeypatch.setattr(scraper.session, "get", fake_get)
    monkeypatch.setattr(scraper.session, "stream_download", fake_stream)

    trial = scraper.search_trials(["oncology"], {}, page=1)[0]
    docs = scraper.fetch_trial_documents(trial.url)
    metadata = scraper.download_documents(
        trial,
        docs,
        output_dir=tmp_path,
        metadata_path=tmp_path / "metadata.jsonl",
        dry_run=False,
    )

    assert metadata.trial_id == "CT-2024-0001"
    assert (tmp_path / trial.trial_id / "protocol.pdf").exists()
    assert (tmp_path / "metadata.jsonl").exists()
