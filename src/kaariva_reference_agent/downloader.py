from __future__ import annotations

from pathlib import Path

import httpx


def download_document(url: str, target_path: Path, timeout: int = 30) -> tuple[bool, str]:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            response = client.get(url)
        if response.status_code >= 400:
            return False, f"http_{response.status_code}"
        content_type = response.headers.get("content-type", "").lower()
        if "pdf" not in content_type and "html" not in content_type:
            return False, "unsupported_format"
        target_path.write_bytes(response.content)
        return True, "ok"
    except httpx.HTTPError:
        return False, "download_error"
