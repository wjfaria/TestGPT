from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ctis_cli.scraper import CTISScraper


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download CTIS trial documents.")
    parser.add_argument("keywords", nargs="+", help="Disease areas or keywords to search")
    parser.add_argument(
        "--therapeutic-area",
        dest="therapeutic_area",
        help="Optional therapeutic area filter",
    )
    parser.add_argument(
        "--field",
        action="append",
        default=[],
        help="Additional CTIS field filters as key=value",
    )
    parser.add_argument(
        "--base-url",
        default="https://euclinicaltrials.eu",
        help="CTIS public portal base URL",
    )
    parser.add_argument("--max-trials", type=int, default=200, help="Maximum trials per run")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Directory to store trial documents",
    )
    parser.add_argument(
        "--metadata-path",
        type=Path,
        default=Path("data") / "metadata.jsonl",
        help="Path to metadata.jsonl",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not download documents")
    parser.add_argument("--ignore-robots", action="store_true", help="Ignore robots.txt rules")
    parser.add_argument(
        "--user-agent",
        default="CTIS-Document-Downloader/1.0",
        help="User-Agent string to identify requests",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="Maximum search result pages to scan",
    )
    return parser.parse_args(argv)


def parse_field_filters(entries: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for entry in entries:
        if "=" not in entry:
            raise ValueError(f"Invalid field filter: {entry}. Expected key=value")
        key, value = entry.split("=", 1)
        fields[key.strip()] = value.strip()
    return fields


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    fields = parse_field_filters(args.field)
    if args.therapeutic_area:
        fields.setdefault("therapeutic_area", args.therapeutic_area)

    scraper = CTISScraper(
        base_url=args.base_url,
        user_agent=args.user_agent,
    )

    trials_processed = 0
    page = 1
    while trials_processed < args.max_trials and page <= args.max_pages:
        trials = scraper.search_trials(
            args.keywords,
            fields,
            page=page,
            ignore_robots=args.ignore_robots,
        )
        if not trials:
            break
        for trial in trials:
            if trials_processed >= args.max_trials:
                break
            documents = scraper.fetch_trial_documents(trial.url, ignore_robots=args.ignore_robots)
            scraper.download_documents(
                trial,
                documents,
                output_dir=args.output_dir,
                metadata_path=args.metadata_path,
                dry_run=args.dry_run,
                ignore_robots=args.ignore_robots,
            )
            trials_processed += 1
        page += 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
