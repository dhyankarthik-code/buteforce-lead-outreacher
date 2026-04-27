"""
Buteforce Lead Outreacher — CSV Cleaner (Step 0)
================================================
Input : "Name sheet - Clients data.csv"
Outputs:
  - leads_clean.csv            → full, cleaned dataset for Marketing Swarm ingestion
  - leads_enrichment_needed.csv → Tier 1 + Tier 2 leads with missing contact data

Run:
  python clean_leads.py
"""

import csv
import re
import os

# ── Config ──────────────────────────────────────────────────────────────────
INPUT_FILE  = "Name sheet - Clients data.csv"
OUT_CLEAN   = "leads_clean.csv"
OUT_ENRICH  = "leads_enrichment_needed.csv"

# EU/GDPR country keywords (case-insensitive substring match on Country column)
GDPR_KEYWORDS = [
    "belgium", "spain", "france", "germany", "netherlands", "ireland",
    "greece", "portugal", "italy", "sweden", "denmark", "finland",
    "austria", "poland", "romania", "bulgaria", "croatia", "czech",
    "slovakia", "slovenia", "estonia", "latvia", "lithuania",
    "hungary", "cyprus", "luxembourg", "malta",
    "united kingdom", "uk",          # UK retains GDPR-equivalent (UK GDPR)
    "switzerland",                    # Swiss nFADP
]

TIER1_THRESHOLD = 200_000   # $200K+
TIER2_THRESHOLD = 50_000    # $50K–$200K
# Below $50K → Tier 3


def parse_spend(raw: str) -> int | None:
    """
    Convert messy spend strings like '$700k+', '3.6M', '300K+', '$2.2K ' → int (USD).
    Returns None if the value cannot be parsed.
    """
    if not raw or not raw.strip():
        return None

    s = raw.strip().upper()

    # Strip leading $ and trailing + whitespace characters
    s = re.sub(r"[\$\+\s]", "", s)

    # Match patterns like  93K / 3.6M / 200+ / 538K / 500k+
    match = re.match(r"^([\d.]+)(K|M)?$", s)
    if not match:
        return None

    number = float(match.group(1))
    suffix = match.group(2)

    if suffix == "K":
        return int(number * 1_000)
    elif suffix == "M":
        return int(number * 1_000_000)
    else:
        return int(number)


def get_tier(spend_usd: int | None) -> int:
    if spend_usd is None:
        return 3   # Unknown spend → lowest priority
    if spend_usd >= TIER1_THRESHOLD:
        return 1
    if spend_usd >= TIER2_THRESHOLD:
        return 2
    return 3


def gdpr_flag(country: str) -> bool:
    lower = country.lower()
    return any(kw in lower for kw in GDPR_KEYWORDS)


def missing_data_label(email: str, linkedin: str) -> str:
    has_email    = bool(email.strip())
    has_linkedin = bool(linkedin.strip())
    if not has_email and not has_linkedin:
        return "both"
    if not has_email:
        return "email_missing"
    if not has_linkedin:
        return "linkedin_missing"
    return ""


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, INPUT_FILE)

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    rows_clean   = []
    rows_enrich  = []

    with open(input_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        original_fields = reader.fieldnames or []

        # Strip BOM / whitespace from field names
        original_fields = [h.strip() for h in original_fields]

        # Define output columns
        extra_cols  = ["spend_usd", "tier", "missing_data", "gdpr_flag"]
        out_fields  = original_fields + extra_cols

        for row in reader:
            # Skip blank rows (all core fields empty)
            company = (row.get("Company Name") or "").strip()
            if not company:
                continue

            # ── Spend normalization ──
            raw_spent  = (row.get("Spent") or "").strip()
            spend_usd  = parse_spend(raw_spent)

            # ── Tier assignment ──
            tier = get_tier(spend_usd)

            # ── Missing data flag ──
            email    = (row.get("Email")    or "").strip()
            linkedin = (row.get("Linkedin") or "").strip()
            missing  = missing_data_label(email, linkedin)

            # ── GDPR flag ──
            country  = (row.get("Company's Country") or "").strip()
            is_gdpr  = gdpr_flag(country)

            # Build enriched row
            clean_row = {h.strip(): (row.get(h) or "").strip() for h in original_fields}
            clean_row["spend_usd"]   = spend_usd if spend_usd is not None else ""
            clean_row["tier"]        = tier
            clean_row["missing_data"] = missing
            clean_row["gdpr_flag"]   = "TRUE" if is_gdpr else "FALSE"

            rows_clean.append(clean_row)

            # Enrichment needed → Tier 1 and Tier 2 with any missing contact data
            if tier in (1, 2) and missing:
                rows_enrich.append(clean_row)

    # ── Write leads_clean.csv ──────────────────────────────────────────────
    out_clean_path = os.path.join(script_dir, OUT_CLEAN)
    with open(out_clean_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(rows_clean)

    # ── Write leads_enrichment_needed.csv ─────────────────────────────────
    out_enrich_path = os.path.join(script_dir, OUT_ENRICH)
    with open(out_enrich_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(rows_enrich)

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n✅ Done.\n")
    print(f"  Total leads processed  : {len(rows_clean)}")
    print(f"  Tier 1 ($200K+)        : {sum(1 for r in rows_clean if r['tier'] == 1)}")
    print(f"  Tier 2 ($50K–$200K)   : {sum(1 for r in rows_clean if r['tier'] == 2)}")
    print(f"  Tier 3 (<$50K)         : {sum(1 for r in rows_clean if r['tier'] == 3)}")
    print(f"  GDPR-flagged leads     : {sum(1 for r in rows_clean if r['gdpr_flag'] == 'TRUE')}")
    print(f"  Missing email          : {sum(1 for r in rows_clean if 'email_missing' in r['missing_data'])}")
    print(f"  Missing both           : {sum(1 for r in rows_clean if r['missing_data'] == 'both')}")
    print(f"\n  → {OUT_CLEAN}           ({len(rows_clean)} rows)")
    print(f"  → {OUT_ENRICH}  ({len(rows_enrich)} rows — Tier 1/2 with gaps)")
    print()


if __name__ == "__main__":
    main()
