from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        sys.exit(f"[config] Missing required environment variable: {key}")
    return val


def _flag(key: str, default: bool = False) -> bool:
    val = os.getenv(key, "").strip().lower()
    if not val:
        return default
    return val in ("1", "true", "yes")


def _list(key: str) -> list[str]:
    val = os.getenv(key, "").strip()
    if not val:
        return []
    return [item.strip() for item in val.split(",") if item.strip()]


def _int(key: str, default: int) -> int:
    val = os.getenv(key, "").strip()
    try:
        return int(val) if val else default
    except ValueError:
        return default


@dataclass(frozen=True)
class Config:
    # --- Required ---
    anthropic_api_key: str
    gmail_address: str
    gmail_app_password: str
    to_email: str
    recipients_file: str

    # --- Feature flags ---
    enable_news: bool
    enable_weather: bool
    enable_calendar: bool
    enable_custom: bool
    enable_market: bool
    enable_sports: bool

    # --- Weather ---
    weather_location: str
    weather_provider: str  # "wttr" or "openweathermap"
    openweathermap_api_key: str

    # --- News ---
    news_feeds: list[str]
    news_max_items_per_feed: int

    # --- Google Calendar ---
    google_credentials_file: str
    google_token_file: str

    # --- Custom URLs ---
    custom_urls: list[str]

    # --- Market ---
    stock_watchlist: list[str]
    enable_crypto: bool
    enable_qqqm_holdings: bool
    qqqm_top_n: int

    # --- Claude tuning ---
    anthropic_model: str
    sms_target_chars: int
    briefing_style: str  # "concise" or "detailed"
    recipient_name: str


def load_config() -> Config:
    return Config(
        # Required
        anthropic_api_key=_require("ANTHROPIC_API_KEY"),
        gmail_address=_require("GMAIL_ADDRESS"),
        gmail_app_password=_require("GMAIL_APP_PASSWORD"),
        to_email=os.getenv("TO_EMAIL", ""),
        recipients_file=os.getenv("RECIPIENTS_FILE", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recipients.json")),

        # Feature flags
        enable_news=_flag("ENABLE_NEWS", default=True),
        enable_weather=_flag("ENABLE_WEATHER", default=True),
        enable_calendar=_flag("ENABLE_CALENDAR", default=False),
        enable_custom=_flag("ENABLE_CUSTOM", default=False),
        enable_market=_flag("ENABLE_MARKET", default=True),
        enable_sports=_flag("ENABLE_SPORTS", default=True),

        # Weather
        weather_location=os.getenv("WEATHER_LOCATION", "New York,US"),
        weather_provider=os.getenv("WEATHER_PROVIDER", "wttr").lower(),
        openweathermap_api_key=os.getenv("OPENWEATHERMAP_API_KEY", ""),

        # News
        news_feeds=_list("NEWS_FEEDS"),
        news_max_items_per_feed=_int("NEWS_MAX_ITEMS_PER_FEED", 5),

        # Calendar
        google_credentials_file=os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials/google_oauth_client.json"),
        google_token_file=os.getenv("GOOGLE_TOKEN_FILE", "credentials/token.json"),

        # Custom
        custom_urls=_list("CUSTOM_URLS"),

        # Market
        stock_watchlist=_list("STOCK_WATCHLIST"),
        enable_crypto=_flag("ENABLE_CRYPTO", default=True),
        enable_qqqm_holdings=_flag("ENABLE_QQQM_HOLDINGS", default=True),
        qqqm_top_n=_int("QQQM_TOP_N", 5),

        # Claude
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5"),
        sms_target_chars=_int("SMS_TARGET_CHARS", 280),
        briefing_style=os.getenv("BRIEFING_STYLE", "concise"),
        recipient_name=os.getenv("RECIPIENT_NAME", ""),
    )
