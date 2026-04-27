"""
Queue store — persists outreach state in queue.json.
Initialises from leads_clean.csv (Tier 1 only) on first run.
"""

import csv
import json
import os
from datetime import datetime

_DIR          = os.path.dirname(os.path.abspath(__file__))
QUEUE_FILE    = os.path.join(_DIR, "queue.json")
LEADS_FILE    = os.path.join(_DIR, "..", "leads_clean.csv")
TRACKER_FILE  = os.path.join(_DIR, "..", "outreach_tracker.csv")


def init_queue() -> list[dict]:
    if os.path.exists(QUEUE_FILE):
        return load_queue()

    leads = []
    seen  = set()  # deduplicate by (company, email)

    with open(LEADS_FILE, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("tier") != "1":
                continue
            key = (row.get("Company Name", "").strip(), row.get("Email", "").strip())
            if key in seen:
                continue
            seen.add(key)

            leads.append({
                "id":           row.get("S. No", "").strip(),
                "company":      row.get("Company Name", "").strip(),
                "contact":      row.get("Contact Name", "").strip(),
                "email":        row.get("Email", "").strip(),
                "linkedin":     row.get("Linkedin", "").strip(),
                "country":      row.get("Company's Country", "").strip(),
                "spent":        row.get("Spent", "").strip(),
                "spend_usd":    row.get("spend_usd", "").strip(),
                "job_type":     row.get("Job type", "").strip(),
                "project_name": row.get("Project Name", "").strip(),
                "job_link":     row.get("Job Link", "").strip(),
                "gdpr_flag":    row.get("gdpr_flag", "FALSE").strip(),
                "missing_data": row.get("missing_data", "").strip(),
                # review state
                "status":       "pending",   # pending | generated | sent | skipped
                "subject":      "",
                "body":         "",
                "generated_at": None,
                "sent_at":      None,
                "notes":        "",
            })

    save_queue(leads)
    return leads


def load_queue() -> list[dict]:
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_queue(queue: list[dict]) -> None:
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)


def get_item(item_id: str) -> dict | None:
    return next(
        (item for item in load_queue() if str(item["id"]) == str(item_id)),
        None,
    )


def update_item(item_id: str, updates: dict) -> dict:
    queue = load_queue()
    for item in queue:
        if str(item["id"]) == str(item_id):
            item.update(updates)
            save_queue(queue)
            return item
    raise ValueError(f"Item {item_id} not found")


def mark_sent(item_id: str, subject: str, body: str) -> dict:
    item = update_item(item_id, {
        "status":  "sent",
        "subject": subject,
        "body":    body,
        "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    _sync_tracker(item)
    return item


def _sync_tracker(sent_item: dict) -> None:
    if not os.path.exists(TRACKER_FILE):
        return

    rows = []
    fieldnames = None

    with open(TRACKER_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            if row.get("Company Name", "").strip() == sent_item["company"]:
                row["email1_sent"]   = sent_item.get("sent_at", "")
                row["email1_replied"] = ""
                row["outcome"]       = "outreached"
            rows.append(row)

    with open(TRACKER_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def queue_stats(queue: list[dict]) -> dict:
    counts = {"pending": 0, "generated": 0, "sent": 0, "skipped": 0, "no_email": 0}
    for item in queue:
        if not item.get("email"):
            counts["no_email"] += 1
        else:
            counts[item.get("status", "pending")] += 1
    return counts
