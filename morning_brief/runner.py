from __future__ import annotations

import argparse
import dataclasses
import json
import sys

from morning_brief.config import load_config
from morning_brief.fetchers.base import FetchResult
from morning_brief.fetchers.weather import WeatherFetcher
from morning_brief.fetchers.news import NewsFetcher
from morning_brief.fetchers.market import MarketFetcher
from morning_brief.fetchers.calendar import CalendarFetcher
from morning_brief.fetchers.custom import CustomFetcher
from morning_brief.fetchers.sports import SportsFetcher
from morning_brief.summarizer import summarize
from morning_brief.sender import send_briefing


def _load_recipients(path: str, mode: str) -> list[dict]:
    try:
        with open(path) as f:
            all_recipients = json.load(f)
    except FileNotFoundError:
        print(f"[runner] recipients file not found: {path}", file=sys.stderr)
        sys.exit(1)
    return [r for r in all_recipients if r.get(mode, False)]


def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["morning", "midday", "afternoon"], default="morning")
    args = parser.parse_args()

    config = load_config()
    recipients = _load_recipients(config.recipients_file, args.mode)

    if not recipients:
        print(f"[runner] No recipients for mode '{args.mode}'. Exiting.")
        sys.exit(0)

    # Fetch shared data once (news, market, calendar, custom)
    shared_results: list[FetchResult] = []

    if config.enable_news:
        print("[runner] Fetching news...")
        shared_results.append(NewsFetcher(config).fetch())

    if config.enable_market:
        print("[runner] Fetching market data...")
        shared_results.append(MarketFetcher(config).fetch())

    if config.enable_calendar:
        print("[runner] Fetching calendar...")
        shared_results.append(CalendarFetcher(config).fetch())

    if config.enable_custom:
        print("[runner] Fetching custom URLs...")
        shared_results.append(CustomFetcher(config).fetch())

    for r in shared_results:
        if not r.success:
            print(f"[runner] WARNING: {r.source_name} failed — {r.error}", file=sys.stderr)

    # Send a personalized briefing to each recipient
    for recipient in recipients:
        name = recipient["name"]
        email = recipient["email"]
        location = recipient.get("location", config.weather_location)

        print(f"[runner] Preparing briefing for {name} ({email})...")

        # Build per-recipient config overrides
        overrides = dict(
            to_email=email,
            recipient_name=name,
            weather_location=location,
            enable_recipes=recipient.get("recipes", False),
        )
        if args.mode in ("midday", "afternoon"):
            overrides["briefing_style"] = args.mode
        recipient_config = dataclasses.replace(config, **overrides)

        results = list(shared_results)

        if recipient_config.enable_weather:
            weather = WeatherFetcher(recipient_config).fetch()
            if not weather.success:
                print(f"[runner] WARNING: Weather failed for {name} — {weather.error}", file=sys.stderr)
            results = [weather] + results

        if recipient_config.enable_sports:
            sports = SportsFetcher(recipient_config).fetch()
            if not sports.success:
                print(f"[runner] WARNING: Sports failed for {name} — {sports.error}", file=sys.stderr)
            else:
                results.append(sports)

        if not results:
            print(f"[runner] No data for {name}, skipping.", file=sys.stderr)
            continue

        print(f"[runner] Summarizing for {name}...")
        briefing = summarize(results, recipient_config)
        print(f"[runner] Briefing for {name} ({len(briefing)} chars):\n{briefing}\n")

        print(f"[runner] Sending email to {email}...")
        try:
            send_briefing(briefing, recipient_config)
            print(f"[runner] Email sent to {email}")
        except Exception as e:
            print(f"[runner] ERROR: Failed to send to {email} — {e}", file=sys.stderr)
