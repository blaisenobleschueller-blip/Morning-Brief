from __future__ import annotations

from html.parser import HTMLParser

import feedparser
import httpx

from morning_brief.config import Config
from morning_brief.fetchers.base import BaseFetcher, FetchResult

ESPN_FEEDS = [
    ("Top Sports", "https://www.espn.com/espn/rss/news"),
    ("NFL", "https://www.espn.com/espn/rss/nfl/news"),
    ("NBA", "https://www.espn.com/espn/rss/nba/news"),
    ("MLB", "https://www.espn.com/espn/rss/mlb/news"),
    ("NHL", "https://www.espn.com/espn/rss/nhl/news"),
]

# Map cities to their teams so the summarizer can pick a local headline
CITY_TEAMS: dict[str, list[str]] = {
    "Chicago": ["Bears", "Bulls", "Cubs", "White Sox", "Blackhawks", "Sky", "Fire"],
    "Manhattan": ["Giants", "Jets", "Knicks", "Nets", "Yankees", "Mets", "Rangers", "Islanders"],
    "Minneapolis": ["Vikings", "Timberwolves", "Twins", "Wild", "Lynx"],
    "New Orleans": ["Saints", "Pelicans"],
    "St Louis": ["Cardinals", "Blues"],
    "Scottsdale": ["Cardinals", "Suns", "Diamondbacks", "Coyotes"],
}


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


def _fetch_feed(url: str, max_items: int = 5) -> list[str]:
    """Fetch top headlines from an RSS feed."""
    try:
        r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True, timeout=10)
        feed = feedparser.parse(r.text)
        lines = []
        for entry in feed.entries[:max_items]:
            title = _strip_html(entry.get("title", ""))
            summary = _strip_html(entry.get("summary", entry.get("description", "")))
            if len(summary) > 150:
                summary = summary[:147] + "..."
            lines.append(f"{title}: {summary}" if summary else title)
        return lines
    except Exception:
        return []


class SportsFetcher(BaseFetcher):
    def __init__(self, config: Config) -> None:
        self._config = config

    def fetch(self) -> FetchResult:
        city = self._config.weather_location.split(",")[0].strip()
        teams = CITY_TEAMS.get(city, [])

        all_headlines: list[str] = []
        for feed_name, url in ESPN_FEEDS:
            headlines = _fetch_feed(url, max_items=3)
            for h in headlines:
                all_headlines.append(f"[{feed_name}] {h}")

        if not all_headlines:
            return FetchResult(source_name="Sports", content="", success=False, error="No sports headlines found")

        content = f"Recipient's local teams: {', '.join(teams)}\n" if teams else ""
        content += "\n".join(all_headlines)

        return FetchResult(source_name="Sports", content=content, success=True)
