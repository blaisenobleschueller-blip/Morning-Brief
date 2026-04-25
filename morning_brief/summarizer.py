from __future__ import annotations

import time
from datetime import date

import anthropic

from morning_brief.config import Config
from morning_brief.fetchers.base import FetchResult


def _build_prompt(results: list[FetchResult], config: Config) -> tuple[str, str]:
    """Return (system_prompt, user_prompt)."""

    today = date.today().strftime("%A, %B %-d, %Y")
    name_part = f" for {config.recipient_name}" if config.recipient_name else ""
    is_afternoon = config.briefing_style == "afternoon" or getattr(config, '_mode', None) == 'afternoon'

    failed = [r.source_name for r in results if not r.success]
    unavailable_note = ""
    if failed:
        unavailable_note = f"\nNote: The following sources were unavailable today: {', '.join(failed)}. Omit those sections."

    if is_afternoon:
        system = f"""You are a sharp, warm afternoon briefing assistant. You write a daily end-of-day email recap{name_part}.

Rules:
- NO markdown, NO bullet symbols, NO asterisks, NO hashtags — plain text only
- Use short punchy sentences separated by line breaks
- Structure: weather update for the evening, then how markets moved today (frame as "today's action"), then 2-3 top news headlines from the day
- Include the QQQM top holdings if provided
- Frame everything as a recap of the day, not a preview of what's ahead
- End with one unique fun fact relevant to today's date or the news, then one short inspiring quote (attributed)
- Target around 800-1000 characters total
- If a section is missing data, skip it silently{unavailable_note}"""
    else:
        system = f"""You are a sharp, warm morning briefing assistant. You write a daily email briefing{name_part}.

Rules:
- NO markdown, NO bullet symbols, NO asterisks, NO hashtags — plain text only
- Use short punchy sentences separated by line breaks
- Structure: weather, then 2-3 top news headlines (ALWAYS include these — never skip news), then market snapshot, then calendar
- Include the QQQM top holdings if provided
- If the market data says "MARKETS ARE CLOSED THIS WEEKEND", mention that markets are closed and frame the numbers as a weekly recap
- End with one unique fun fact relevant to today's date or the news, then one short inspiring quote (attributed)
- Target around 800-1000 characters total
- If a section is missing data, skip it silently{unavailable_note}"""

    # Build the data sections
    sections: list[str] = [f"Today is {today}.\n"]
    for r in results:
        if r.success and r.content:
            sections.append(f"[{r.source_name.upper()}]\n{r.content}")

    time_of_day = "afternoon" if is_afternoon else "morning"
    user = "\n\n".join(sections) + f"\n\nWrite the {time_of_day} briefing now."

    return system, user


def summarize(results: list[FetchResult], config: Config, retries: int = 2) -> str:
    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    system, user = _build_prompt(results, config)

    max_tokens = 1024

    for attempt in range(retries + 1):
        try:
            message = client.messages.create(
                model=config.anthropic_model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return message.content[0].text.strip()
        except anthropic.APIStatusError as e:
            if attempt < retries and e.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            raise
