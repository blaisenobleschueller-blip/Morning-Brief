from __future__ import annotations

import json
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

from morning_brief.config import Config
from morning_brief.fetchers.base import BaseFetcher, FetchResult

_TIMEOUT = 15
_MAX_CHARS = 500


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._title: str = ""
        self._in_title = False
        self._skip_tags = {"script", "style", "nav", "header", "footer"}
        self._active_skip = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "title":
            self._in_title = True
        if tag in self._skip_tags:
            self._active_skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag in self._skip_tags:
            self._active_skip = max(0, self._active_skip - 1)

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self._title = text
        elif self._active_skip == 0:
            self._parts.append(text)

    def get_text(self) -> str:
        body = " ".join(self._parts)
        if self._title:
            return f"{self._title}: {body}"
        return body


def _extract_html(html: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(html)
    text = extractor.get_text()
    return text[:_MAX_CHARS] + "..." if len(text) > _MAX_CHARS else text


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc or url
    except Exception:
        return url


class CustomFetcher(BaseFetcher):
    def __init__(self, config: Config) -> None:
        self._config = config

    def fetch(self) -> FetchResult:
        if not self._config.custom_urls:
            return FetchResult(
                source_name="Custom",
                content="No custom URLs configured.",
                success=True,
            )
        blocks: list[str] = []
        for url in self._config.custom_urls:
            block = self._fetch_url(url)
            if block:
                blocks.append(block)

        if not blocks:
            return FetchResult(source_name="Custom", content="", success=False, error="All custom URLs failed")

        return FetchResult(source_name="Custom", content="\n\n".join(blocks), success=True)

    def _fetch_url(self, url: str) -> str:
        try:
            resp = httpx.get(url, timeout=_TIMEOUT, follow_redirects=True)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            domain = _domain(url)

            if "json" in content_type:
                data = resp.json()
                text = json.dumps(data, indent=None)[:_MAX_CHARS]
                return f"=== {domain} ===\n{text}"
            elif "html" in content_type:
                text = _extract_html(resp.text)
                return f"=== {domain} ===\n{text}"
            else:
                text = resp.text[:_MAX_CHARS]
                return f"=== {domain} ===\n{text}"
        except Exception:
            return ""  # Silent per-URL failure
