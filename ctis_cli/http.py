from __future__ import annotations

import ssl
import time
from dataclasses import dataclass
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class BackoffConfig:
    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 16.0


@dataclass
class SimpleResponse:
    status_code: int
    text: str
    url: str

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code} for {self.url}")


class RateLimitedSession:
    def __init__(
        self,
        user_agent: str,
        max_requests_per_second: float = 1.0,
        backoff: BackoffConfig | None = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
    ) -> None:
        self._headers = {"User-Agent": user_agent}
        self._min_interval = 1.0 / max_requests_per_second
        self._last_request_at: float | None = None
        self._backoff = backoff or BackoffConfig()
        self._timeout = timeout
        self._ssl_context = (
            ssl.create_default_context() if verify_ssl else ssl._create_unverified_context()
        )

    def _sleep_if_needed(self) -> None:
        if self._last_request_at is None:
            return
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)

    def _request(self, url: str) -> SimpleResponse:
        request = Request(url, headers=self._headers)
        try:
            with urlopen(request, timeout=self._timeout, context=self._ssl_context) as response:
                content = response.read()
                text = content.decode("utf-8", errors="replace")
                return SimpleResponse(status_code=response.status, text=text, url=url)
        except HTTPError as err:
            content = err.read()
            text = content.decode("utf-8", errors="replace")
            return SimpleResponse(status_code=err.code, text=text, url=url)
        except URLError as err:
            raise RuntimeError(f"Request failed for {url}: {err}") from err

    def _request_with_backoff(self, url: str) -> SimpleResponse:
        attempt = 0
        delay = self._backoff.base_delay
        while True:
            self._sleep_if_needed()
            self._last_request_at = time.monotonic()
            response = self._request(url)
            if response.status_code not in {429} and response.status_code < 500:
                return response
            attempt += 1
            if attempt > self._backoff.max_retries:
                return response
            time.sleep(delay)
            delay = min(delay * 2, self._backoff.max_delay)

    def get(self, url: str) -> SimpleResponse:
        return self._request_with_backoff(url)

    def stream_download(self, url: str, chunk_size: int = 8192) -> Iterable[bytes]:
        attempt = 0
        delay = self._backoff.base_delay
        while True:
            self._sleep_if_needed()
            self._last_request_at = time.monotonic()
            request = Request(url, headers=self._headers)
            try:
                with urlopen(
                    request,
                    timeout=self._timeout,
                    context=self._ssl_context,
                ) as response:
                    status_code = response.status
                    if status_code in {429} or status_code >= 500:
                        raise HTTPError(url, status_code, "retry", response.headers, None)
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
                    return
            except HTTPError as err:
                attempt += 1
                if attempt > self._backoff.max_retries:
                    raise RuntimeError(f"HTTP {err.code} for {url}") from err
                time.sleep(delay)
                delay = min(delay * 2, self._backoff.max_delay)
            except URLError as err:
                raise RuntimeError(f"Request failed for {url}: {err}") from err
