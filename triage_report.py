"""
Buteforce Lead Outreacher — Enrichment Triage Report (Unit B)
=============================================================
Reads leads_enrichment_needed.csv and prints a ranked priority list
for manual enrichment (Apollo.io / Hunter.io).

Priority order:
  1. Tier 1 first (highest spend = highest value)
  2. Within tier: sort by spend_usd descending
  3. Within same spend: email_missing before linkedin_missing (email harder to get)

Run:
  python triage_report.py
"""

import csv
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(SCRIPT_DIR, "leads_enrichment_needed.csv")

SEGMENT_MAP = {
    "voice": "Voice AI / RAG",
    "rag":   "Voice AI / RAG",
    "livekit": "Voice AI / RAG",
    "n8n":   "N8N / LangChain",
    "langchain": "N8N / LangChain",
    "automation": "N8N / LangChain",
    "vision": "Computer Vision",
    "cv":    "Computer Vision",
    "orthotics": "Computer Vision",
    "web":   "Full-Stack / Web Dev",
    "wordpress": "Full-Stack / Web Dev",
    "backend": "Full-Stack / Web Dev",
}

MISSING_PRIORITY = {"both": 0, "email_missing": 1, "linkedin_missing": 2}


def detect_segment(job_type: str, project_name: str) -> str:
    text = (job_type + " " + project_name).lower()
    for keyword, segment in SEGMENT_MAP.items():
        if keyword in text:
            return segment
    return "AI / General"


def format_spend(spend_usd: str) -> str:
    try:
        v = int(spend_usd)
        if v >= 1_000_000:
            return f"${v/1_000_000:.1f}M"
        if v >= 1_000:
            return f"${v//1_000}K"
        return f"${v}"
    except (ValueError, TypeError):
        return "?"


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"File not found: {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Filter only leads with actual gaps
    gaps = [r for r in rows if r.get("missing_data", "")]

    # Sort: tier asc, spend_usd desc, missing priority asc
    gaps.sort(key=lambda r: (
        int(r.get("tier", 3)),
        -int(r.get("spend_usd") or 0),
        MISSING_PRIORITY.get(r.get("missing_data", ""), 3)
    ))

    tier1 = [r for r in gaps if r.get("tier") == "1"]
    tier2 = [r for r in gaps if r.get("tier") == "2"]

    SEP = "-" * 80

    def print_section(title: str, leads: list):
        print(f"\n{SEP}")
        print(f"  {title}  ({len(leads)} leads)")
        print(f"{SEP}")
        print(f"  {'#':<3}  {'Spend':<8}  {'Company':<28}  {'Contact':<22}  {'Missing':<18}  {'GDPR':<5}  Segment")
        print(f"  {'-'*3}  {'-'*8}  {'-'*28}  {'-'*22}  {'-'*18}  {'-'*5}  {'-'*20}")
        for i, r in enumerate(leads, 1):
            company  = r.get("Company Name", "")[:27]
            contact  = r.get("Contact Name", "")[:21]
            spend    = format_spend(r.get("spend_usd"))
            missing  = r.get("missing_data", "")
            gdpr     = "! YES" if r.get("gdpr_flag") == "TRUE" else "no"
            segment  = detect_segment(r.get("Job type", ""), r.get("Project Name", ""))
            print(f"  {i:<3}  {spend:<8}  {company:<28}  {contact:<22}  {missing:<18}  {gdpr:<5}  {segment}")
            # Show manual lookup hints
            email    = r.get("Email", "").strip()
            linkedin = r.get("Linkedin", "").strip()
            link     = r.get("Link", "").strip()
            if email:
                print(f"       Email: {email}")
            else:
                domain = link.replace("https://","").replace("http://","").replace("www.","").strip("/ ")
                print(f"       Email: MISSING — try Apollo.io | domain: {domain}")
            if linkedin:
                print(f"       LinkedIn: {linkedin}")
            else:
                print(f"       LinkedIn: MISSING — Google: site:linkedin.com/in \"{r.get('Contact Name','').strip()}\" \"{r.get('Company Name','').strip()}\"")

    EQ = "=" * 80
    print(f"\n{EQ}")
    print("  BUTEFORCE - MANUAL ENRICHMENT TRIAGE REPORT")
    print(f"  Total leads needing enrichment: {len(gaps)}")
    print(f"{EQ}")

    print_section("TIER 1  ($200K+)  - DO THESE FIRST", tier1)
    print_section("TIER 2  ($50K-$200K)", tier2)

    print(f"\n{EQ}")
    print(f"  Summary")
    print(f"  Tier 1 gaps  : {len(tier1)}")
    print(f"  Tier 2 gaps  : {len(tier2)}")
    print(f"  GDPR-flagged : {sum(1 for r in gaps if r.get('gdpr_flag')=='TRUE')}")
    print(f"  Both missing : {sum(1 for r in gaps if r.get('missing_data')=='both')}")
    print(f"{EQ}\n")


if __name__ == "__main__":
    main()
