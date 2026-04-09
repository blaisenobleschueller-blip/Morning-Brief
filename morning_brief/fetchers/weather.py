from __future__ import annotations

import json
import httpx

from morning_brief.config import Config
from morning_brief.fetchers.base import BaseFetcher, FetchResult

_TIMEOUT = 10


class WeatherFetcher(BaseFetcher):
    def __init__(self, config: Config) -> None:
        self._config = config

    def fetch(self) -> FetchResult:
        try:
            if self._config.weather_provider == "openweathermap":
                content = self._fetch_openweathermap()
            else:
                content = self._fetch_wttr()
            return FetchResult(source_name="Weather", content=content, success=True)
        except Exception as e:
            return FetchResult(source_name="Weather", content="", success=False, error=str(e))

    def _fetch_wttr(self) -> str:
        location = self._config.weather_location
        # format=4 gives: "Location: condition temp (feels like), humidity, wind"
        url = f"https://wttr.in/{location}?format=%l:+%C,+%t+(feels+like+%f),+humidity+%h,+wind+%w"
        resp = httpx.get(url, timeout=_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        return resp.text.strip()

    def _fetch_openweathermap(self) -> str:
        key = self._config.openweathermap_api_key
        if not key:
            raise ValueError("OPENWEATHERMAP_API_KEY is not set")
        location = self._config.weather_location
        url = "https://api.openweathermap.org/data/2.5/weather"
        resp = httpx.get(
            url,
            params={"q": location, "appid": key, "units": "imperial"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        condition = data["weather"][0]["description"].capitalize()
        temp = data["main"]["temp"]
        feels = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        wind = data["wind"]["speed"]
        city = data["name"]
        return f"{city}: {condition}, {temp:.0f}°F (feels like {feels:.0f}°F), humidity {humidity}%, wind {wind:.0f} mph"
