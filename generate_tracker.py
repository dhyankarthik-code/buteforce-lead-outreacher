"""
Buteforce Lead Outreacher — Outreach Tracker Generator (Unit D)
===============================================================
Reads leads_clean.csv, filters Tier 1 leads, and writes
outreach_tracker.csv — a state-tracking sheet for manual outreach.

Columns added:
  linkedin_sent       | date (YYYY-MM-DD) or blank
  linkedin_accepted   | yes / no / blank
  email1_sent         | date or blank
  email1_replied      | yes / no / blank
  email2_sent         | date or blank
  email2_replied      | yes / no / blank
  audit_offered       | yes / no / blank
  audit_booked        | yes / no / blank
  outcome             | converted / nurture / dead / blank
  notes               | free text

Run:
  python generate_tracker.py
"""

import csv
import os

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE   = os.path.join(SCRIPT_DIR, "leads_clean.csv")
OUTPUT_FILE  = os.path.join(SCRIPT_DIR, "outreach_tracker.csv")

TRACKING_COLS = [
    "linkedin_sent",
    "linkedin_accepted",
    "email1_sent",
    "email1_replied",
    "email2_sent",
    "email2_replied",
    "audit_offered",
    "audit_booked",
    "outcome",
    "notes",
]

SEGMENT_MAP = {
    "voice":       "Voice AI / RAG",
    "rag":         "Voice AI / RAG",
    "livekit":     "Voice AI / RAG",
    "speech":      "Voice AI / RAG",
    "chatbot":     "Voice AI / RAG",
    "n8n":         "N8N / LangChain",
    "langchain":   "N8N / LangChain",
    "langgraph":   "N8N / LangChain",
    "automation":  "N8N / LangChain",
    "workflow":    "N8N / LangChain",
    "vision":      "Computer Vision",
    "image":       "Computer Vision",
    "detection":   "Computer Vision",
    "orthotics":   "Computer Vision",
    "web":         "Full-Stack / Web Dev",
    "wordpress":   "Full-Stack / Web Dev",
    "backend":     "Full-Stack / Web Dev",
}


def detect_segment(job_type: str, project_name: str) -> str:
    text = (job_type + " " + project_name).lower()
    for kw, seg in SEGMENT_MAP.items():
        if kw in text:
            return seg
    return "AI / General"


def format_spend(spend_usd: str) -> str:
    try:
        v = int(spend_usd)
        if v >= 1_000_000:
            return f"${v / 1_000_000:.1f}M"
        if v >= 1_000:
            return f"${v // 1_000}K"
        return f"${v}"
    except (ValueError, TypeError):
        return "?"


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"File not found: {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows   = list(reader)

    tier1 = [r for r in rows if r.get("tier") == "1"]
    # Sort by spend_usd descending (highest value first)
    tier1.sort(key=lambda r: -int(r.get("spend_usd") or 0))

    out_fields = [
        "priority",
        "Company Name",
        "Contact Name",
        "spend_display",
        "segment",
        "Email",
        "Linkedin",
        "gdpr_flag",
        "missing_data",
        "Job type",
        "Project Name",
        "Job Link",
    ] + TRACKING_COLS

    out_rows = []
    for i, r in enumerate(tier1, 1):
        out_row = {
            "priority":      i,
            "Company Name":  r.get("Company Name", ""),
            "Contact Name":  r.get("Contact Name", ""),
            "spend_display": format_spend(r.get("spend_usd", "")),
            "segment":       detect_segment(r.get("Job type", ""), r.get("Project Name", "")),
            "Email":         r.get("Email", ""),
            "Linkedin":      r.get("Linkedin", ""),
            "gdpr_flag":     r.get("gdpr_flag", "FALSE"),
            "missing_data":  r.get("missing_data", ""),
            "Job type":      r.get("Job type", ""),
            "Project Name":  r.get("Project Name", ""),
            "Job Link":      r.get("Job Link", ""),
        }
        # Tracking columns start blank
        for col in TRACKING_COLS:
            out_row[col] = ""
        out_rows.append(out_row)

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"\nDone. outreach_tracker.csv written - {len(out_rows)} Tier 1 leads")
    print(f"   Open in Excel / Google Sheets to track outreach state.\n")

    # Quick summary
    gdpr_count    = sum(1 for r in out_rows if r["gdpr_flag"] == "TRUE")
    missing_count = sum(1 for r in out_rows if r["missing_data"])
    print(f"   GDPR-flagged : {gdpr_count}  (must include opt-out footer)")
    print(f"   Need enrichment first : {missing_count}  (run triage_report.py)")
    print()


if __name__ == "__main__":
    main()
