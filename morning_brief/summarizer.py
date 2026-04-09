from __future__ import annotations

from datetime import date

import anthropic

from morning_brief.config import Config
from morning_brief.fetchers.base import FetchResult


def _build_prompt(results: list[FetchResult], config: Config) -> tuple[str, str]:
    """Return (system_prompt, user_prompt)."""

    today = date.today().strftime("%A, %B %-d, %Y")
    name_part = f" for {config.recipient_name}" if config.recipient_name else ""

    failed = [r.source_name for r in results if not r.success]
    unavailable_note = ""
    if failed:
        unavailable_note = f"\nNote: The following sources were unavailable today: {', '.join(failed)}. Omit those sections."

    max_tokens_hint = config.sms_target_chars
    style_note = (
        "Be very concise — target under 300 characters total."
        if config.briefing_style == "concise"
        else f"Aim for around {max_tokens_hint} characters."
    )

    system = f"""You are a sharp, warm morning briefing assistant. You write a daily SMS briefing{name_part}.

Rules:
- NO markdown, NO bullet symbols, NO asterisks, NO hashtags — plain text only (SMS renders these as clutter)
- Use short punchy sentences separated by line breaks
- Lead with weather, then top news headline, then market snapshot, then calendar
- Include the QQQM top holdings if provided
- End with one unique fun fact relevant to today's date or the news, then one short inspiring quote (attributed)
- {style_note}
- If a section is missing data, skip it silently{unavailable_note}"""

    # Build the data sections
    sections: list[str] = [f"Today is {today}.\n"]
    for r in results:
        if r.success and r.content:
            sections.append(f"[{r.source_name.upper()}]\n{r.content}")

    user = "\n\n".join(sections) + "\n\nWrite the morning briefing now."

    return system, user


def summarize(results: list[FetchResult], config: Config) -> str:
    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    system, user = _build_prompt(results, config)

    max_tokens = 512 if config.briefing_style == "concise" else 1024

    message = client.messages.create(
        model=config.anthropic_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )

    return message.content[0].text.strip()
