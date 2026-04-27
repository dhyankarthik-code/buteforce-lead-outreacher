"""
Sheets store — reads/writes Google Sheets as the lead database.

Sheet: "Clients detail" in the Buteforce spreadsheet.
Original columns A-N stay untouched.
Tracking state is written to columns O-T (added by this app).

Column map (0-indexed):
  A(0)  S. No          → id
  B(1)  Company Name   → company
  C(2)  Contact Name   → contact
  E(4)  Company Country → country
  F(5)  Email          → email
  H(7)  Linkedin       → linkedin
  K(10) Spent          → spent / spend_usd
  L(11) Job type       → job_type
  M(12) Project Name   → project_name
  N(13) Job Link       → job_link
  O(14) status         ← written by app
  P(15) subject        ← written by app
  Q(16) body           ← written by app
  R(17) generated_at   ← written by app
  S(18) sent_at        ← written by app
  T(19) notes          ← written by app
"""

import json
import os
import re
import time
from datetime import datetime
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

SHEET_ID   = os.environ.get("SHEET_ID",   "1KghW03YIgrvWhSPzKTgw_uyGU2BcMVtB5nP1tPZUdfQ")
SHEET_NAME = os.environ.get("SHEET_NAME", "Clients detail")
SCOPES     = ["https://www.googleapis.com/auth/spreadsheets"]

TRACK_START = "O"
TRACK_END   = "T"

EU_COUNTRIES = {
    "austria", "belgium", "bulgaria", "croatia", "cyprus", "czech republic",
    "denmark", "estonia", "finland", "france", "germany", "greece", "hungary",
    "ireland", "italy", "latvia", "lithuania", "luxembourg", "malta", "netherlands",
    "poland", "portugal", "romania", "slovakia", "slovenia", "spain", "sweden",
    "norway", "iceland", "liechtenstein", "united kingdom", "uk",
}

# Simple in-memory cache so rapid UI interactions don't hammer the Sheets API.
_cache: Optional[list[dict]] = None
_cache_ts: float = 0.0
_CACHE_TTL = 8.0  # seconds


def _bust_cache() -> None:
    global _cache, _cache_ts
    _cache = None
    _cache_ts = 0.0


def _get_sheet() -> gspread.Worksheet:
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON is not set. "
            "Paste the full service-account JSON as a single-line env var."
        )
    info  = json.loads(sa_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    gc    = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)


def _parse_spend(raw: str) -> int:
    raw = raw.strip().upper()
    raw = re.sub(r"[$,\s]", "", raw)
    multiplier = 1
    if raw.endswith("K"):
        multiplier = 1_000
        raw = raw[:-1]
    elif raw.endswith("M"):
        multiplier = 1_000_000
        raw = raw[:-1]
    try:
        return int(float(raw) * multiplier)
    except (ValueError, TypeError):
        return 0


def _row_to_lead(row: list[str], sheet_row: int) -> Optional[dict]:
    def cell(i: int) -> str:
        return row[i].strip() if i < len(row) else ""

    spend_usd = _parse_spend(cell(10))
    if spend_usd < 200_000:
        return None  # Tier 1 only

    country  = cell(4)
    email    = cell(5)
    linkedin = cell(7)

    missing = ", ".join(filter(None, [
        "email"    if not email    else "",
        "linkedin" if not linkedin else "",
    ]))

    return {
        "id":           cell(0) or str(sheet_row),
        "company":      cell(1),
        "contact":      cell(2),
        "email":        email,
        "linkedin":     linkedin,
        "country":      country,
        "spent":        cell(10),
        "spend_usd":    str(spend_usd),
        "job_type":     cell(11),
        "project_name": cell(12),
        "job_link":     cell(13),
        "gdpr_flag":    "TRUE" if country.strip().lower() in EU_COUNTRIES else "FALSE",
        "missing_data": missing,
        # tracking state (cols O-T)
        "status":       cell(14) or "pending",
        "subject":      cell(15),
        "body":         cell(16),
        "generated_at": cell(17) or None,
        "sent_at":      cell(18) or None,
        "notes":        cell(19),
        # internal — used for row-level writes; stripped before responses
        "_sheet_row":   sheet_row,
    }


def _load_from_sheet() -> list[dict]:
    sheet    = _get_sheet()
    all_rows = sheet.get_all_values()
    if not all_rows:
        return []

    leads = []
    seen  = set()
    for i, row in enumerate(all_rows[1:], start=2):  # row 1 = header → data starts at 2
        lead = _row_to_lead(row, i)
        if lead is None:
            continue
        key = (lead["company"].lower(), lead["email"].lower())
        if key in seen:
            continue
        seen.add(key)
        leads.append(lead)
    return leads


def load_queue() -> list[dict]:
    global _cache, _cache_ts
    if _cache is not None and (time.monotonic() - _cache_ts) < _CACHE_TTL:
        return _cache
    _cache    = _load_from_sheet()
    _cache_ts = time.monotonic()
    return _cache


def init_queue() -> list[dict]:
    return load_queue()


def get_item(item_id: str) -> Optional[dict]:
    return next(
        (item for item in load_queue() if str(item["id"]) == str(item_id)),
        None,
    )


def _write_tracking(sheet: gspread.Worksheet, sheet_row: int, item: dict) -> None:
    values    = [[
        item.get("status",       "pending"),
        item.get("subject",      ""),
        item.get("body",         ""),
        item.get("generated_at") or "",
        item.get("sent_at")      or "",
        item.get("notes",        ""),
    ]]
    range_name = f"{TRACK_START}{sheet_row}:{TRACK_END}{sheet_row}"
    sheet.update(range_name=range_name, values=values)


def update_item(item_id: str, updates: dict) -> dict:
    sheet = _get_sheet()
    queue = _load_from_sheet()

    item = next((i for i in queue if str(i["id"]) == str(item_id)), None)
    if item is None:
        raise ValueError(f"Item {item_id} not found")

    item.update(updates)
    _write_tracking(sheet, item["_sheet_row"], item)
    _bust_cache()
    return item


def mark_sent(item_id: str, subject: str, body: str) -> dict:
    return update_item(item_id, {
        "status":  "sent",
        "subject": subject,
        "body":    body,
        "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })


def queue_stats(queue: list[dict]) -> dict:
    counts = {"pending": 0, "generated": 0, "sent": 0, "skipped": 0, "no_email": 0}
    for item in queue:
        if not item.get("email"):
            counts["no_email"] += 1
        else:
            counts[item.get("status", "pending")] += 1
    return counts
