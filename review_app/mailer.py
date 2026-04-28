"""
Mailer — sends branded HTML + plain-text email via SMTP.
Reads credentials from environment variables.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from email_template import build_html_email


def send_email(to: str, subject: str, body: str) -> tuple[bool, str]:
    """
    Send a multipart (plain + HTML) email.
    Returns (success: bool, error_message: str).
    """
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "admin@buteforce.com")
    smtp_pass = os.environ.get("SMTP_PASS", "")

    if not smtp_pass:
        return False, (
            "SMTP_PASS is not set. "
            "Add your Google Workspace app password to review_app/.env"
        )
    if not to or "@" not in to:
        return False, f"Invalid recipient address: {to!r}"

    msg             = MIMEMultipart("alternative")
    msg["From"]     = f"Dhyaneshwaran Karthikeyan <{smtp_user}>"
    msg["To"]       = to
    msg["Subject"]  = subject
    msg["Reply-To"] = smtp_user

    # Plain text fallback (email clients that can't render HTML)
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # Branded HTML — attached last so clients prefer it
    try:
        html_body = build_html_email(body)
        msg.attach(MIMEText(html_body, "html", "utf-8"))
    except Exception:
        pass  # degrade gracefully to plain text if template fails

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [to], msg.as_string())
        return True, ""
    except smtplib.SMTPAuthenticationError:
        return False, (
            "SMTP authentication failed. "
            "Check SMTP_USER and SMTP_PASS — use a Google Workspace App Password, "
            "not your regular account password."
        )
    except smtplib.SMTPRecipientsRefused:
        return False, f"Recipient refused by server: {to}"
    except Exception as exc:
        return False, str(exc)
