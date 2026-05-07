from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


def _load_domains_from_simple_yaml(path: Path) -> set[str]:
    domains: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("-"):
            domains.add(line.removeprefix("-").strip())
    return domains


class Allowlist:
    def __init__(self, config_path: str = "config/source_allowlist.yaml") -> None:
        self.domains = _load_domains_from_simple_yaml(Path(config_path))

    def is_allowed(self, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return any(host == d or host.endswith(f".{d}") for d in self.domains)
