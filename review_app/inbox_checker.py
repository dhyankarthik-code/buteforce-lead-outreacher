"""
Inbox checker — polls IMAP inbox for replies to sent outreach.
Classifies each reply with Gemini: classification, reason, suggested_action.
"""

import email as email_lib
import imaplib
import json
import os
import re
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime

IMAP_HOST = os.environ.get("IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.environ.get("IMAP_PORT", "993"))
SMTP_USER = os.environ.get("SMTP_USER", "admin@buteforce.com")
SMTP_PASS = os.environ.get("SMTP_PASS", "")


def _decode_str(h: str) -> str:
    if not h:
        return ""
    parts = decode_header(h)
    out = []
    for part, enc in parts:
        if isinstance(part, bytes):
            out.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(part)
    return "".join(out)


def _extract_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                cs = part.get_content_charset() or "utf-8"
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(cs, errors="replace")
    else:
        cs = msg.get_content_charset() or "utf-8"
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(cs, errors="replace")
    return ""


def _parse_date(date_str: str) -> str:
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return date_str or ""


def fetch_replies(sent_leads: list[dict]) -> list[dict]:
    """
    Check IMAP INBOX for replies from leads we've sent to.
    Returns list of unclassified reply dicts.
    """
    if not SMTP_PASS:
        return []

    lead_by_email = {
        lead["email"].lower(): lead
        for lead in sent_leads
        if lead.get("email") and lead.get("status") == "sent"
    }
    if not lead_by_email:
        return []

    replies = []
    try:
        with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) as imap:
            imap.login(SMTP_USER, SMTP_PASS)
            imap.select("INBOX", readonly=True)

            for email_addr, lead in lead_by_email.items():
                status, data = imap.search(None, f'FROM "{email_addr}"')
                if status != "OK" or not data[0]:
                    continue

                for num in data[0].split()[-20:]:
                    try:
                        status2, msg_data = imap.fetch(num, "(RFC822)")
                        if status2 != "OK":
                            continue
                        raw = msg_data[0][1]
                        msg = email_lib.message_from_bytes(raw)

                        subject     = _decode_str(msg.get("Subject", ""))
                        msg_id      = msg.get("Message-ID", "").strip()
                        in_reply_to = msg.get("In-Reply-To", "").strip()
                        date_str    = msg.get("Date", "")

                        if not (subject.lower().startswith("re:") or in_reply_to):
                            continue

                        body = _extract_body(msg)
                        _, from_clean = parseaddr(msg.get("From", ""))

                        replies.append({
                            "id":               msg_id or f"imap_{num.decode()}_{email_addr}",
                            "lead_id":          str(lead["id"]),
                            "company":          lead["company"],
                            "recipient_email":  email_addr,
                            "original_subject": lead.get("subject", ""),
                            "reply_subject":    subject,
                            "reply_from":       from_clean or email_addr,
                            "reply_body":       body[:3000],
                            "reply_at":         _parse_date(date_str),
                            "classification":   None,
                            "reason":           None,
                            "suggested_action": None,
                            "read":             False,
                        })
                    except Exception:
                        continue
    except Exception:
        pass

    return replies


def classify_reply(body: str, company: str) -> dict:
    """Use Gemini to classify a reply. Returns {classification, reason, suggested_action}."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {
            "classification":   "other",
            "reason":           "No API key configured",
            "suggested_action": "Review manually",
        }

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL", "gemini-2.5-pro"))

        prompt = f"""You are analyzing a reply to a cold outreach email sent by Buteforce \
(a precision AI systems company) to {company}.

Reply:
---
{body[:1500]}
---

Classify as exactly one of:
- interested        (positive, wants to learn more or move forward)
- meeting_requested (wants to schedule a call or meeting)
- question          (asking specific questions about the offer)
- not_interested    (polite or direct decline)
- out_of_office     (automated OOO reply)
- unsubscribe       (wants to be removed)
- other             (anything else)

Return JSON only:
{{
  "classification": "<one of above>",
  "reason": "<one sentence explaining the signal>",
  "suggested_action": "<one specific next step, e.g. 'Reply with portfolio + schedule a call'>"
}}"""

        resp  = model.generate_content(prompt)
        text  = resp.text.strip()
        match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass

    return {
        "classification":   "other",
        "reason":           "Classification unavailable",
        "suggested_action": "Review manually",
    }
