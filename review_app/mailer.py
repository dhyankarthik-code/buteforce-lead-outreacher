"""
Mailer — sends email via SMTP (Google Workspace or any SMTP relay).
Reads credentials from environment variables.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(to: str, subject: str, body: str) -> tuple[bool, str]:
    """
    Send a plain-text email.
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
    msg["From"]     = smtp_user
    msg["To"]       = to
    msg["Subject"]  = subject
    msg["Reply-To"] = smtp_user
    msg.attach(MIMEText(body, "plain", "utf-8"))

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
