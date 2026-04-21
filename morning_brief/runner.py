from __future__ import annotations

import sys

from morning_brief.config import load_config
from morning_brief.fetchers.base import FetchResult
from morning_brief.fetchers.weather import WeatherFetcher
from morning_brief.fetchers.news import NewsFetcher
from morning_brief.fetchers.market import MarketFetcher
from morning_brief.fetchers.calendar import CalendarFetcher
from morning_brief.fetchers.custom import CustomFetcher
from morning_brief.summarizer import summarize
from morning_brief.sender import send_sms


def run() -> None:
    config = load_config()

    results: list[FetchResult] = []

    if config.enable_weather:
        print("[runner] Fetching weather...")
        results.append(WeatherFetcher(config).fetch())

    if config.enable_news:
        print("[runner] Fetching news...")
        results.append(NewsFetcher(config).fetch())

    if config.enable_market:
        print("[runner] Fetching market data...")
        results.append(MarketFetcher(config).fetch())

    if config.enable_calendar:
        print("[runner] Fetching calendar...")
        results.append(CalendarFetcher(config).fetch())

    if config.enable_custom:
        print("[runner] Fetching custom URLs...")
        results.append(CustomFetcher(config).fetch())

    # Log any fetch failures
    for r in results:
        if not r.success:
            print(f"[runner] WARNING: {r.source_name} failed — {r.error}", file=sys.stderr)

    if not results:
        print("[runner] No data sources enabled. Exiting.", file=sys.stderr)
        sys.exit(1)

    print("[runner] Summarizing with Claude...")
    briefing = summarize(results, config)
    print(f"[runner] Briefing ({len(briefing)} chars):\n{briefing}\n")

    print("[runner] Sending SMS via Gmail...")
    try:
        sid = send_sms(briefing, config)
        print(f"[runner] SMS sent. SID: {sid}")
    except Exception as e:
        print(f"[runner] ERROR: Failed to send SMS — {e}", file=sys.stderr)
        print(f"[runner] Briefing text (unsent):\n{briefing}", file=sys.stderr)
        sys.exit(1)
