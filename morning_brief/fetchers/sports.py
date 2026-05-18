from __future__ import annotations

import httpx

from morning_brief.config import Config
from morning_brief.fetchers.base import BaseFetcher, FetchResult

ESPN_LEAGUES = [
    ("NFL", "football", "nfl"),
    ("NBA", "basketball", "nba"),
    ("MLB", "baseball", "mlb"),
    ("NHL", "hockey", "nhl"),
]

# Map cities to their teams so the summarizer can highlight local results
CITY_TEAMS: dict[str, list[str]] = {
    "Chicago": ["Bears", "Bulls", "Cubs", "White Sox", "Blackhawks", "Sky", "Fire"],
    "Manhattan": ["Giants", "Jets", "Knicks", "Nets", "Yankees", "Mets", "Rangers", "Islanders"],
    "Minneapolis": ["Vikings", "Timberwolves", "Twins", "Wild", "Lynx"],
    "New Orleans": ["Saints", "Pelicans"],
    "St Louis": ["Cardinals", "Blues"],
    "Scottsdale": ["Cardinals", "Suns", "Diamondbacks", "Coyotes"],
}

_TIMEOUT = 10


def _format_game(event: dict) -> str:
    """Format a single ESPN event into a readable line."""
    competition = event["competitions"][0]
    status_type = event["status"]["type"]
    state = status_type["state"]  # "pre", "in", "post"
    detail = event["status"]["type"].get("shortDetail", status_type["description"])

    competitors = competition["competitors"]
    # ESPN lists home team first (index 0), away team second (index 1)
    home = competitors[0]
    away = competitors[1]

    home_name = home["team"]["displayName"]
    away_name = away["team"]["displayName"]

    if state == "post":
        home_score = home.get("score", "?")
        away_score = away.get("score", "?")
        winner = home_name if home.get("winner") else away_name
        return f"{away_name} {away_score}, {home_name} {home_score} (Final) — {winner} win"
    elif state == "in":
        home_score = home.get("score", "?")
        away_score = away.get("score", "?")
        return f"{away_name} {away_score}, {home_name} {home_score} ({detail})"
    else:
        return f"{away_name} at {home_name} ({detail})"


def _fetch_league(sport: str, league: str) -> list[str]:
    """Fetch today's scoreboard for a league."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    try:
        r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=_TIMEOUT)
        r.raise_for_status()
        events = r.json().get("events", [])
        return [_format_game(e) for e in events]
    except Exception:
        return []


class SportsFetcher(BaseFetcher):
    def __init__(self, config: Config) -> None:
        self._config = config

    def fetch(self) -> FetchResult:
        city = self._config.weather_location.split(",")[0].strip()
        teams = CITY_TEAMS.get(city, [])

        sections: list[str] = []
        any_games = False

        for label, sport, league in ESPN_LEAGUES:
            games = _fetch_league(sport, league)
            if games:
                any_games = True
                sections.append(f"{label}:\n" + "\n".join(f"  {g}" for g in games))
            else:
                sections.append(f"{label}: No games today")

        if not any_games:
            return FetchResult(
                source_name="Sports",
                content="No games scheduled across major leagues today.",
                success=True,
            )

        header = f"Recipient's local teams: {', '.join(teams)}\n\n" if teams else ""
        content = header + "\n\n".join(sections)

        return FetchResult(source_name="Sports", content=content, success=True)
