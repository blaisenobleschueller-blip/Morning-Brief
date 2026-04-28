from __future__ import annotations

import smtplib
from email.mime.text import MIMEText

from morning_brief.config import Config


def send_briefing(body: str, config: Config) -> None:
    """Send the morning briefing via Gmail SMTP."""
    msg = MIMEText(body, "plain")
    subjects = {"afternoon": "Afternoon Brief", "midday": "Midday Brief"}
    msg["Subject"] = subjects.get(config.briefing_style, "Morning Brief")
    msg["From"] = config.gmail_address
    msg["To"] = config.to_email

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(config.gmail_address, config.gmail_app_password)
        server.sendmail(config.gmail_address, config.to_email, msg.as_string())
