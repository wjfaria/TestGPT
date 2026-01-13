from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urlencode, urljoin, urlparse

from ctis_cli.http import RateLimitedSession
from ctis_cli.models import DownloadedDocument, TrialDocument, TrialMetadata, TrialSummary


class RobotsRules:
    def __init__(self, rules_by_agent: dict[str, list[str]]) -> None:
        self._rules_by_agent = rules_by_agent

    @classmethod
    def from_text(cls, content: str) -> "RobotsRules":
        rules_by_agent: dict[str, list[str]] = {}
        current_agents: list[str] = []
        for raw_line in content.splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()
            if key == "user-agent":
                current_agents = [value.lower()]
                rules_by_agent.setdefault(value.lower(), [])
            elif key == "disallow" and current_agents:
                for agent in current_agents:
                    rules_by_agent.setdefault(agent, []).append(value)
        return cls(rules_by_agent)

    def is_allowed(self, user_agent: str, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path or "/"
        agents = [user_agent.lower(), "*"]
        for agent in agents:
            disallows = self._rules_by_agent.get(agent)
            if not disallows:
                continue
            for disallow in disallows:
                if not disallow:
                    continue
                if path.startswith(disallow):
                    return False
        return True


class CTISScraper:
    def __init__(
        self,
        base_url: str,
        user_agent: str,
        max_requests_per_second: float = 1.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = RateLimitedSession(
            user_agent=user_agent,
            max_requests_per_second=max_requests_per_second,
        )
        self.user_agent = user_agent
        self._robots_rules: RobotsRules | None = None

    def ensure_robots(self) -> RobotsRules:
        if self._robots_rules is None:
            robots_url = urljoin(self.base_url + "/", "robots.txt")
            response = self.session.get(robots_url)
            if response.ok:
                self._robots_rules = RobotsRules.from_text(response.text)
            else:
                self._robots_rules = RobotsRules({})
        return self._robots_rules

    def _guard_robots(self, url: str, ignore_robots: bool) -> None:
        if ignore_robots:
            return
        rules = self.ensure_robots()
        if not rules.is_allowed(self.user_agent, url):
            raise RuntimeError(f"Blocked by robots.txt for {url}")

    def build_search_url(self, keywords: Iterable[str], fields: dict[str, str], page: int) -> str:
        params = {"search": " ".join(keywords), "page": page}
        params.update({k: v for k, v in fields.items() if v})
        return f"{self.base_url}/search?{urlencode(params)}"

    def search_trials(
        self,
        keywords: Iterable[str],
        fields: dict[str, str],
        page: int = 1,
        ignore_robots: bool = False,
    ) -> list[TrialSummary]:
        search_url = self.build_search_url(keywords, fields, page)
        self._guard_robots(search_url, ignore_robots)
        response = self.session.get(search_url)
        response.raise_for_status()
        return parse_search_results(response.text, self.base_url)

    def fetch_trial_documents(
        self,
        trial_url: str,
        ignore_robots: bool = False,
    ) -> list[TrialDocument]:
        self._guard_robots(trial_url, ignore_robots)
        response = self.session.get(trial_url)
        response.raise_for_status()
        return parse_trial_documents(response.text, trial_url)

    def download_documents(
        self,
        trial: TrialSummary,
        documents: Iterable[TrialDocument],
        output_dir: Path,
        metadata_path: Path,
        dry_run: bool,
        ignore_robots: bool = False,
    ) -> TrialMetadata:
        trial_dir = output_dir / trial.trial_id
        trial_dir.mkdir(parents=True, exist_ok=True)

        downloaded_docs: list[DownloadedDocument] = []
        for document in documents:
            destination = trial_dir / document.filename
            if destination.exists():
                downloaded_docs.append(
                    DownloadedDocument(
                        title=document.title,
                        url=document.url,
                        filename=document.filename,
                        sha256=sha256_file(destination),
                        downloaded_at=datetime.now(timezone.utc).isoformat(),
                        doc_type=document.doc_type,
                    )
                )
                continue
            if dry_run:
                continue
            self._guard_robots(document.url, ignore_robots)
            with destination.open("wb") as handle:
                for chunk in self.session.stream_download(document.url):
                    handle.write(chunk)
            downloaded_docs.append(
                DownloadedDocument(
                    title=document.title,
                    url=document.url,
                    filename=document.filename,
                    sha256=sha256_file(destination),
                    downloaded_at=datetime.now(timezone.utc).isoformat(),
                    doc_type=document.doc_type,
                )
            )
        metadata = TrialMetadata(
            trial_id=trial.trial_id,
            title=trial.title,
            condition=trial.condition,
            url=trial.url,
            documents=downloaded_docs,
        )
        write_metadata(metadata_path, metadata)
        return metadata


from html.parser import HTMLParser


class _SearchParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.results: list[TrialSummary] = []
        self._current_trial: dict[str, str] | None = None
        self._in_link = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key: value or "" for key, value in attrs}
        trial_id = attrs_dict.get("data-trial-id")
        if trial_id:
            self._current_trial = {
                "trial_id": trial_id.strip(),
                "condition": attrs_dict.get("data-condition", "").strip(),
                "url": "",
                "title": "",
            }
        if tag == "a":
            href = attrs_dict.get("href", "")
            class_name = attrs_dict.get("class", "")
            if self._current_trial and not self._current_trial["url"]:
                self._current_trial["url"] = urljoin(self.base_url + "/", href)
                self._in_link = True
            elif "trial-link" in class_name:
                self._current_trial = {
                    "trial_id": trial_id.strip() if trial_id else "",
                    "condition": attrs_dict.get("data-condition", "").strip(),
                    "url": urljoin(self.base_url + "/", href),
                    "title": "",
                }
                self._in_link = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_trial and self._in_link:
            trial_id = self._current_trial.get("trial_id") or self._current_trial.get("title")
            url = self._current_trial.get("url")
            if trial_id and url:
                self.results.append(
                    TrialSummary(
                        trial_id=trial_id.strip(),
                        title=(self._current_trial.get("title") or trial_id).strip(),
                        condition=self._current_trial.get("condition", "").strip(),
                        url=url,
                    )
                )
            self._current_trial = None
            self._in_link = False

    def handle_data(self, data: str) -> None:
        if self._current_trial is not None and self._in_link:
            self._current_trial["title"] += data.strip()


class _DocumentsParser(HTMLParser):
    def __init__(self, trial_url: str) -> None:
        super().__init__()
        self.trial_url = trial_url
        self.documents: list[TrialDocument] = []
        self._current_doc: dict[str, str] | None = None
        self._capture_text = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attrs_dict = {key: value or "" for key, value in attrs}
        href = attrs_dict.get("href", "")
        if not href:
            return
        if not href.lower().endswith(".pdf") and "document-download" not in attrs_dict.get("class", ""):
            return
        url = urljoin(self.trial_url, href)
        filename = Path(urlparse(url).path).name or "document.pdf"
        self._current_doc = {
            "url": url,
            "filename": filename,
            "title": "",
            "doc_type": attrs_dict.get("data-doc-type", "").strip(),
        }
        self._capture_text = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_doc and self._capture_text:
            title = self._current_doc.get("title") or self._current_doc.get("filename")
            doc_type = self._current_doc.get("doc_type") or None
            self.documents.append(
                TrialDocument(
                    title=title.strip(),
                    url=self._current_doc["url"],
                    filename=self._current_doc["filename"],
                    doc_type=doc_type,
                )
            )
            self._current_doc = None
            self._capture_text = False

    def handle_data(self, data: str) -> None:
        if self._current_doc is not None and self._capture_text:
            self._current_doc["title"] += data.strip()


def parse_search_results(html: str, base_url: str) -> list[TrialSummary]:
    parser = _SearchParser(base_url=base_url)
    parser.feed(html)
    return parser.results


def parse_trial_documents(html: str, trial_url: str) -> list[TrialDocument]:
    parser = _DocumentsParser(trial_url=trial_url)
    parser.feed(html)
    return parser.documents


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_metadata(metadata_path: Path, metadata: TrialMetadata) -> None:
    record = asdict(metadata)
    record["documents"] = [asdict(doc) for doc in metadata.documents]
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
