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
                try:
                    content = self._fetch_wttr()
                except Exception:
                    # Fallback to OpenWeatherMap if wttr.in is down
                    if self._config.openweathermap_api_key:
                        content = self._fetch_openweathermap()
                    else:
                        raise
            return FetchResult(source_name="Weather", content=content, success=True)
        except Exception as e:
            return FetchResult(source_name="Weather", content="", success=False, error=str(e))

    def _fetch_wttr(self) -> str:
        location = self._config.weather_location
        # Get current conditions
        current_url = f"https://wttr.in/{location}?format=%l:+%C,+%t+(feels+like+%f),+humidity+%h,+wind+%w"
        resp = httpx.get(current_url, timeout=_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        current = resp.text.strip()

        # Get forecast (JSON format for today's forecast including rain/snow)
        forecast_url = f"https://wttr.in/{location}?format=j1"
        resp2 = httpx.get(forecast_url, timeout=_TIMEOUT, follow_redirects=True)
        resp2.raise_for_status()
        data = resp2.json()

        forecast_parts = [current]
        today = data.get("weather", [{}])[0]
        if today:
            high = today.get("maxtempF", "")
            low = today.get("mintempF", "")
            if high and low:
                forecast_parts.append(f"High {high}°F, Low {low}°F")
            hourly = today.get("hourly", [])
            precip_hours = []
            for h in hourly:
                chance = int(h.get("chanceofrain", "0"))
                if chance >= 30:
                    time_val = int(h.get("time", "0"))
                    hour_label = f"{time_val // 100}:00" if time_val else "0:00"
                    precip_hours.append(f"{hour_label} ({chance}%)")
            if precip_hours:
                forecast_parts.append(f"Rain likely: {', '.join(precip_hours)}")
            snow_hours = []
            for h in hourly:
                chance = int(h.get("chanceofsnow", "0"))
                if chance >= 30:
                    time_val = int(h.get("time", "0"))
                    hour_label = f"{time_val // 100}:00" if time_val else "0:00"
                    snow_hours.append(f"{hour_label} ({chance}%)")
            if snow_hours:
                forecast_parts.append(f"Snow likely: {', '.join(snow_hours)}")

        return "\n".join(forecast_parts)

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
