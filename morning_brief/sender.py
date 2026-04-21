from __future__ import annotations

import smtplib
from email.mime.text import MIMEText

from morning_brief.config import Config


def send_sms(body: str, config: Config) -> None:
    """Send the briefing via Gmail SMTP to a carrier email-to-SMS gateway."""
    msg = MIMEText(body)
    msg["From"] = config.gmail_address
    msg["To"] = config.sms_to_address
    msg["Subject"] = ""

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(config.gmail_address, config.gmail_app_password)
        server.send_message(msg)
