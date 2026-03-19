from __future__ import annotations

from dataclasses import dataclass
from urllib import request
from urllib.error import HTTPError, URLError


@dataclass
class _Response:
    response: object

    def __post_init__(self):
        self.headers = dict(self.response.headers.items())
        self.status_code = getattr(self.response, "status", 200)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def close(self):
        self.response.close()

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPError(self.response.url, self.status_code, "HTTP error", self.response.headers, None)

    def iter_content(self, chunk_size=8192):
        while True:
            chunk = self.response.read(chunk_size)
            if not chunk:
                break
            yield chunk


def get(url, stream=False, timeout=60):
    del stream
    try:
        return _Response(request.urlopen(url, timeout=timeout))
    except URLError as exc:
        raise RuntimeError(f"Request failed: {exc}") from exc
