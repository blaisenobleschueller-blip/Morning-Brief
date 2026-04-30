from __future__ import annotations

import os
import time
from datetime import date

import anthropic

from morning_brief.config import Config
from morning_brief.fetchers.base import FetchResult

USED_QUOTES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "used_quotes.txt")


def _load_recent_quotes(limit: int = 60) -> list[str]:
    try:
        with open(USED_QUOTES_FILE) as f:
            quotes = [line.strip() for line in f if line.strip()]
        return quotes[-limit:]
    except FileNotFoundError:
        return []


def _save_quote(quote: str) -> None:
    with open(USED_QUOTES_FILE, "a") as f:
        f.write(quote + "\n")


def _build_prompt(results: list[FetchResult], config: Config) -> tuple[str, str]:
    """Return (system_prompt, user_prompt)."""

    today = date.today().strftime("%A, %B %-d, %Y")
    name_part = f" for {config.recipient_name}" if config.recipient_name else ""
    is_midday = config.briefing_style == "midday"
    is_afternoon = config.briefing_style == "afternoon" or getattr(config, '_mode', None) == 'afternoon'

    failed = [r.source_name for r in results if not r.success]
    unavailable_note = ""
    if failed:
        unavailable_note = f"\nNote: The following sources were unavailable today: {', '.join(failed)}. Omit those sections."

    recent_quotes = _load_recent_quotes()
    if recent_quotes:
        quotes_block = "\n\nDo NOT use any of these previously used quotes:\n" + "\n".join(f"- {q}" for q in recent_quotes)
    else:
        quotes_block = ""

    recipe_block = ""
    if config.enable_recipes:
        recipe_block = "\n- After the quote, include a RECIPE OF THE DAY: a simple, tasty recipe focusing on high fiber and/or high protein. Include the dish name, a 2-3 sentence description of the flavors, and a quick ingredient list and steps. Keep it to ~150 words. Choose a different recipe every day — vary across cuisines and meal types (breakfast, lunch, dinner, snacks)."

    if is_midday:
        system = f"""You are a sharp, warm midday briefing assistant. You write a daily lunchtime email update{name_part}.

Rules:
- NO markdown, NO bullet symbols, NO asterisks, NO hashtags — plain text only
- ALWAYS start with the day and date (e.g. "Sunday, April 27, 2026") as the first line after the greeting
- Use short punchy sentences separated by line breaks
- This is the MIDDAY update. The recipient already received a morning briefing today. DO NOT repeat the same news headlines, weather details, or market numbers from this morning. Focus on what has CHANGED or is NEW since the morning.
- Structure: any weather changes or afternoon forecast, then midday market movers and notable shifts since the open, then 2-3 NEW news stories that broke since the morning, then sports (pick one top general headline and one about the recipient's local teams)
- Include updated QQQM and watchlist performance only if there are notable intraday moves
- End with one unique fun fact relevant to today's date or the news, then one short inspiring quote (attributed). IMPORTANT: Choose a different quote every day and a different quote from the morning brief — never repeat recent quotes. Draw from a wide range of authors, leaders, athletes, scientists, and philosophers.
- Target around 800-1000 characters total
- If a section is missing data, skip it silently{unavailable_note}{quotes_block}{recipe_block}"""
    elif is_afternoon:
        system = f"""You are a sharp, warm afternoon briefing assistant. You write a daily end-of-day email recap{name_part}.

Rules:
- NO markdown, NO bullet symbols, NO asterisks, NO hashtags — plain text only
- ALWAYS start with the day and date (e.g. "Sunday, April 27, 2026") as the first line after the greeting
- Use short punchy sentences separated by line breaks
- Structure: weather update for the evening (include forecast details like rain/snow chances if present), then how markets moved today (frame as "today's action"), then 2-3 top news headlines from the day, then sports (pick one top general headline and one about the recipient's local teams)
- Include the QQQM top holdings if provided
- Frame everything as a recap of the day, not a preview of what's ahead
- End with one unique fun fact relevant to today's date or the news, then one short inspiring quote (attributed). IMPORTANT: Choose a different quote every day — never repeat recent quotes. Draw from a wide range of authors, leaders, athletes, scientists, and philosophers.
- Target around 800-1000 characters total
- If a section is missing data, skip it silently{unavailable_note}{quotes_block}{recipe_block}"""
    else:
        system = f"""You are a sharp, warm morning briefing assistant. You write a daily email briefing{name_part}.

Rules:
- NO markdown, NO bullet symbols, NO asterisks, NO hashtags — plain text only
- ALWAYS start with the day and date (e.g. "Sunday, April 27, 2026") as the first line after the greeting
- Use short punchy sentences separated by line breaks
- Structure: weather (include forecast details like rain/snow chances if present), then 2-3 top news headlines (ALWAYS include these — never skip news), then market snapshot, then sports (pick one top general headline and one headline about the recipient's local teams — if no local team news, just use two general), then calendar
- Include the QQQM top holdings if provided
- If the market data says "MARKETS ARE CLOSED THIS WEEKEND", mention that markets are closed and frame the numbers as a weekly recap
- End with one unique fun fact relevant to today's date or the news, then one short inspiring quote (attributed). IMPORTANT: Choose a different quote every day — never repeat recent quotes. Draw from a wide range of authors, leaders, athletes, scientists, and philosophers.
- Target around 800-1000 characters total
- If a section is missing data, skip it silently{unavailable_note}{quotes_block}{recipe_block}"""

    # Build the data sections
    sections: list[str] = [f"Today is {today}.\n"]
    for r in results:
        if r.success and r.content:
            sections.append(f"[{r.source_name.upper()}]\n{r.content}")

    time_of_day = "midday" if is_midday else ("afternoon" if is_afternoon else "morning")
    user = "\n\n".join(sections) + f"\n\nWrite the {time_of_day} briefing now."

    return system, user


def summarize(results: list[FetchResult], config: Config, retries: int = 2) -> str:
    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    system, user = _build_prompt(results, config)

    max_tokens = 1280 if config.enable_recipes else 1024

    for attempt in range(retries + 1):
        try:
            message = client.messages.create(
                model=config.anthropic_model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            text = message.content[0].text.strip()

            # Extract and save the quote (last non-empty line that looks like a quote)
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            if lines:
                last_line = lines[-1]
                if last_line.startswith('"') or last_line.startswith('\u201c'):
                    _save_quote(last_line)

            return text
        except anthropic.APIStatusError as e:
            if attempt < retries and e.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            raise
