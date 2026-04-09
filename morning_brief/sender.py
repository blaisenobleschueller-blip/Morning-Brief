from __future__ import annotations

from twilio.rest import Client

from morning_brief.config import Config


def send_sms(body: str, config: Config) -> str:
    """Send the briefing via Twilio SMS. Returns the message SID."""
    client = Client(config.twilio_account_sid, config.twilio_auth_token)
    message = client.messages.create(
        body=body,
        from_=config.twilio_from_number,
        to=config.twilio_to_number,
    )
    return message.sid
