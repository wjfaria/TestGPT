from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from ctis_cli.models import TrialDocument, TrialSummary
from ctis_cli.scraper import CTISScraper


@dataclass
class BrowserSearchConfig:
    search_page_url: str = "https://euclinicaltrials.eu/search-for-clinical-trials/?lang=en"
    headless: bool = True
    max_pages: int = 50


def _find_first_selector(page, selectors: Iterable[str]):
    for selector in selectors:
        element = page.query_selector(selector)
        if element is not None:
            return element
    return None


def _unique_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _trial_id_from_url(url: str) -> str:
    return Path(urlparse(url).path).name or url


def _documents_from_urls(urls: Iterable[str]) -> list[TrialDocument]:
    documents: list[TrialDocument] = []
    for url in _unique_preserve_order(urls):
        filename = Path(urlparse(url).path).name or "document.pdf"
        documents.append(
            TrialDocument(
                title=filename,
                url=url,
                filename=filename,
                doc_type=None,
            )
        )
    return documents


def run_browser_download(
    keywords: Iterable[str],
    therapeutic_area: str,
    output_dir: Path,
    metadata_path: Path,
    max_trials: int,
    max_pages: int,
    user_agent: str,
    verify_ssl: bool,
    ignore_robots: bool,
    config: BrowserSearchConfig | None = None,
) -> int:
    config = config or BrowserSearchConfig(max_pages=max_pages)
    search_terms = " ".join(keywords)
    scraper = CTISScraper(
        base_url="https://euclinicaltrials.eu/ctis-public",
        user_agent=user_agent,
        verify_ssl=verify_ssl,
    )
    trials_processed = 0

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=config.headless)
        context = browser.new_context(
            user_agent=user_agent,
            ignore_https_errors=not verify_ssl,
        )
        page = context.new_page()
        page.goto(config.search_page_url, wait_until="networkidle")

        search_input = _find_first_selector(
            page,
            [
                "input[type='search']",
                "input[name='search']",
                "input[placeholder*='Search']",
                "input[aria-label*='Search']",
            ],
        )
        if search_input is None:
            browser.close()
            raise RuntimeError("Could not find the search input on the CTIS page.")
        search_input.fill(search_terms)

        if therapeutic_area:
            area_input = _find_first_selector(
                page,
                [
                    "input[placeholder*='Therapeutic']",
                    "input[aria-label*='Therapeutic']",
                    "input[name*='therapeutic']",
                    "select[name*='therapeutic']",
                ],
            )
            if area_input is not None:
                area_input.fill(therapeutic_area)
            else:
                print(
                    "Warning: could not find therapeutic area input; continuing without it.",
                    file=sys.stderr,
                )

        submit_button = _find_first_selector(
            page,
            [
                "button[type='submit']",
                "button:has-text('Search')",
                "button:has-text('Apply')",
            ],
        )
        if submit_button is None:
            browser.close()
            raise RuntimeError("Could not find the search submit button on the CTIS page.")
        submit_button.click()

        page_index = 1
        while trials_processed < max_trials and page_index <= config.max_pages:
            try:
                page.wait_for_selector("a[href*='/trial/']", timeout=10000)
            except PlaywrightTimeoutError:
                print("No trial links detected on this page.", file=sys.stderr)

            trial_links = page.eval_on_selector_all(
                "a[href*='/trial/']",
                "els => els.map(el => el.href)",
            )
            trial_links = _unique_preserve_order(trial_links)
            if not trial_links:
                break

            for trial_url in trial_links:
                if trials_processed >= max_trials:
                    break
                page.goto(trial_url, wait_until="networkidle")

                title_element = _find_first_selector(
                    page,
                    [
                        "h1",
                        "[data-testid='trial-title']",
                        "h2",
                    ],
                )
                title = title_element.inner_text().strip() if title_element else trial_url
                trial_summary = TrialSummary(
                    trial_id=_trial_id_from_url(trial_url),
                    title=title,
                    condition="",
                    url=trial_url,
                )

                documents_tab = _find_first_selector(
                    page,
                    [
                        "a:has-text('Documents')",
                        "button:has-text('Documents')",
                        "a:has-text('Trial documents')",
                    ],
                )
                if documents_tab is not None:
                    documents_tab.click()
                    page.wait_for_timeout(1500)

                doc_urls = page.eval_on_selector_all(
                    "a[href$='.pdf'], a.document-download",
                    "els => els.map(el => el.href)",
                )
                documents = _documents_from_urls(doc_urls)
                scraper.download_documents(
                    trial_summary,
                    documents,
                    output_dir=output_dir,
                    metadata_path=metadata_path,
                    dry_run=False,
                    ignore_robots=ignore_robots,
                )
                trials_processed += 1

            next_button = _find_first_selector(
                page,
                [
                    "a[rel='next']",
                    "button:has-text('Next')",
                    "a:has-text('Next')",
                    "button:has-text('›')",
                ],
            )
            if next_button is None:
                break
            next_button.click()
            page_index += 1

        browser.close()

    return trials_processed
