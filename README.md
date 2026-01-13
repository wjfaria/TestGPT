# CTIS CLI Downloader

A Python CLI tool for searching the EU CTIS public portal and downloading publicly available trial documents (including protocol PDFs when present). The tool is designed for polite crawling with rate limits, exponential backoff, resume support, and metadata tracking.

## Features

- Search CTIS trials by disease area/keywords.
- Optional CTIS field filters such as therapeutic area (`--therapeutic-area`) or custom key/value filters (`--field therapeutic_area=Oncology`).
- Download trial documents into `data/{trial_id}/` using the portal's document links.
- Polite crawling: 1 request/second, exponential backoff on 429/5xx, and per-run trial caps.
- Respects robots.txt (with `--ignore-robots` escape hatch) and identifies itself via User-Agent.
- Resume support (skips already-downloaded documents).
- Writes `metadata.jsonl` with document URLs, download timestamps, and SHA-256 checksums.
- Includes a desktop GUI for entering keywords and selecting an output folder.
- Unit tests with mocked HTTP responses.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### macOS quick start (find the repo and run the GUI)

If you already downloaded/cloned the repo but are not sure where it lives, this block finds
the directory that contains `pyproject.toml`, installs the package, and launches the GUI:

```bash
REPO_DIR="$(mdfind "kMDItemFSName == 'pyproject.toml'" | head -n 1 | xargs -I{} dirname "{}")"
cd "$REPO_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
ctis-gui
```

If `mdfind` returns nothing, you can locate the repo manually and then run the same steps
from that directory:

```bash
open ~
```

## CLI Usage

Search for oncology trials and download protocol documents:

```bash
ctis-cli oncology --therapeutic-area Oncology
```

If you see SSL certificate errors on your network, you can disable verification (not recommended):

```bash
ctis-cli oncology --therapeutic-area Oncology --insecure
```

Search for multiple disease areas with a per-run cap and dry run:

```bash
ctis-cli oncology asthma diabetes --max-trials 50 --dry-run
```

Add additional CTIS filters:

```bash
ctis-cli diabetes --field therapeutic_area=Endocrinology --field study_phase=Phase%203
```

Override the CTIS base URL (useful for testing/mirroring):

```bash
ctis-cli oncology --base-url https://euclinicaltrials.eu
```

## GUI Usage

Launch the GUI:

```bash
ctis-gui
```

In the GUI, enter comma-separated keywords (e.g., `oncology, asthma`), optionally set a therapeutic area, choose an output folder, and click **Start**. Downloads are saved in the selected output directory.

If your network intercepts SSL certificates, enable **Disable SSL verification (insecure)** in the GUI.

## Build a macOS executable

On macOS, you can build a standalone executable using PyInstaller:

```bash
pip install -e .[gui]
pyinstaller --onefile --windowed --name ctis-gui ctis_cli/gui.py
```

The executable will be located in `dist/ctis-gui`. You can move it anywhere on your Mac and double-click to run.

## Output

Downloaded documents are stored in:

```
data/{trial_id}/
```

Metadata is appended to:

```
data/metadata.jsonl
```

Each record includes trial metadata, document URLs, download timestamps, and SHA-256 checksums.

## Development

Run tests:

```bash
pytest
```
