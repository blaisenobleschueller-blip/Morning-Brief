from __future__ import annotations

import re
from html.parser import HTMLParser

import feedparser

from morning_brief.config import Config
from morning_brief.fetchers.base import BaseFetcher, FetchResult


class _HTMLStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts)


def _strip_html(text: str) -> str:
    if not text:
        return ""
    stripper = _HTMLStripper()
    stripper.feed(text)
    return stripper.get_text().strip()


class NewsFetcher(BaseFetcher):
    def __init__(self, config: Config) -> None:
        self._config = config

    def fetch(self) -> FetchResult:
        if not self._config.news_feeds:
            return FetchResult(
                source_name="News",
                content="No news feeds configured.",
                success=True,
            )
        blocks: list[str] = []
        for url in self._config.news_feeds:
            block = self._fetch_feed(url)
            if block:
                blocks.append(block)

        if not blocks:
            return FetchResult(source_name="News", content="", success=False, error="All news feeds failed")

        return FetchResult(source_name="News", content="\n\n".join(blocks), success=True)

    def _fetch_feed(self, url: str) -> str:
        try:
            feed = feedparser.parse(url)
            feed_title = feed.feed.get("title", url)
            entries = feed.entries[: self._config.news_max_items_per_feed]
            if not entries:
                return f"=== {feed_title} ===\n(No recent entries)"
            lines = [f"=== {feed_title} ==="]
            for i, entry in enumerate(entries, 1):
                title = _strip_html(entry.get("title", "Untitled"))
                summary = _strip_html(entry.get("summary", entry.get("description", "")))
                # Truncate long summaries
                if len(summary) > 200:
                    summary = summary[:197] + "..."
                if summary:
                    lines.append(f"{i}. {title}: {summary}")
                else:
                    lines.append(f"{i}. {title}")
            return "\n".join(lines)
        except Exception as e:
            return ""  # Silent per-feed failure; other feeds still included
