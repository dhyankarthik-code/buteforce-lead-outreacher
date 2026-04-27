"""
Buteforce Lead Outreacher — Auto Enricher (Step 1)
===================================================
Uses Tavily Search + Gemini (Flash) to automatically
find missing Email and LinkedIn profiles for leads.

Improvements over v1:
  - Exponential backoff on rate-limit errors (429)
  - Per-API consecutive-failure quota guard (skips lead after 3 API fails)
  - Incremental writes (saves after each lead — safe to interrupt and resume)
  - Skips leads already fully enriched

Run:
  python auto_enrich.py
"""

import os
import csv
import json
import time
import urllib.request
import urllib.error

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE  = os.path.join(SCRIPT_DIR, "leads_enrichment_needed.csv")
CLEAN_FILE  = os.path.join(SCRIPT_DIR, "leads_clean.csv")
ENV_FILE    = os.path.join(SCRIPT_DIR, r"..\Marketing agents\buteforce-marketing-swarm\.env")

# Backoff config
MAX_RETRIES      = 3
BACKOFF_BASE_SEC = 5   # first retry after 5s, then 10s, then 20s
QUOTA_FAIL_LIMIT = 3   # skip current lead's API call after this many consecutive 429s


def load_env() -> dict:
    env_vars = {}
    if not os.path.exists(ENV_FILE):
        return env_vars
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip().strip("'\"")
    return env_vars


def _http_post(url: str, payload: dict, headers: dict) -> dict | None:
    """POST with exponential backoff on 429. Returns parsed JSON or None."""
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(url, data=data, headers=headers)

    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = BACKOFF_BASE_SEC * (2 ** attempt)
                print(f"    [429 rate-limit] backing off {wait}s (attempt {attempt+1}/{MAX_RETRIES})")
                time.sleep(wait)
            else:
                print(f"    [HTTPError {e.code}] {e.reason}")
                return None
        except urllib.error.URLError as e:
            print(f"    [URLError] {e.reason}")
            return None

    print(f"    [quota-guard] gave up after {MAX_RETRIES} retries — skipping this call")
    return None


def tavily_search(query: str, api_key: str) -> str:
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": 3,
        "include_domains": ["linkedin.com"] if "linkedin" in query.lower() else []
    }
    res = _http_post(
        "https://api.tavily.com/search",
        payload,
        {"Content-Type": "application/json"}
    )
    if not res:
        return ""
    snippets = [
        r.get("content", "") + " | URL: " + r.get("url", "")
        for r in res.get("results", [])
    ]
    return "\n".join(snippets)


def gemini_extract(context: str, api_key: str, mode: str) -> str:
    """Extract a URL or email from search-result context using Gemini Flash."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta"
        f"/models/gemini-2.0-flash:generateContent?key={api_key}"
    )

    if mode == "linkedin":
        prompt = (
            "Extract the most likely personal LinkedIn Profile URL from the following "
            "search results. Return ONLY the raw URL (e.g. https://www.linkedin.com/in/johndoe). "
            "If you cannot find one, return exactly None.\nResults:\n\n" + context
        )
    else:
        prompt = (
            "Extract the most likely email address from the following search results. "
            "Return ONLY the raw email (e.g. john@company.com). "
            "If you cannot find one, return exactly None.\nResults:\n\n" + context
        )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 100}
    }
    res = _http_post(url, payload, {"Content-Type": "application/json"})
    if not res:
        return ""

    try:
        val = res["candidates"][0]["content"]["parts"][0]["text"].strip()
        return val if "None" not in val else ""
    except (KeyError, IndexError):
        return ""


def main():
    print("Loading APIs...")
    env        = load_env()
    tavily_key = env.get("TAVILY_API_KEY")
    gemini_key = env.get("GOOGLE_AI_API_KEY")

    if not tavily_key or not gemini_key:
        print("Missing TAVILY_API_KEY or GOOGLE_AI_API_KEY. Enrichment aborted.")
        return

    if not os.path.exists(INPUT_FILE):
        print(f"No file found at {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader    = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows      = list(reader)

    print(f"Loaded {len(rows)} leads. Processing Tier 1 & 2 with gaps...\n")

    # Track consecutive API quota failures across leads to detect full exhaustion
    tavily_quota_fails = 0
    gemini_quota_fails = 0

    for idx, row in enumerate(rows):
        tier    = row.get("tier", "3")
        missing = row.get("missing_data", "")

        if tier not in ["1", "2"] or missing == "":
            continue

        company  = row.get("Company Name", "").strip()
        contact  = row.get("Contact Name", "").strip()
        email    = row.get("Email", "").strip()
        linkedin = row.get("Linkedin", "").strip()

        print(f"[{idx+1}/{len(rows)}] Tier {tier} | {company} | {contact} | Missing: {missing}")

        # ── LinkedIn search ─────────────────────────────────────────────────
        if ("linkedin" in missing or missing == "both") and not linkedin:
            if tavily_quota_fails >= QUOTA_FAIL_LIMIT:
                print("  [quota-guard] Tavily quota exhausted — skipping LinkedIn search")
            else:
                q = (
                    f'"{contact}" "{company}" site:linkedin.com/in'
                    if contact
                    else f'"{company}" founder OR CEO site:linkedin.com/in'
                )
                search_res = tavily_search(q, tavily_key)
                if search_res:
                    tavily_quota_fails = 0
                else:
                    tavily_quota_fails += 1

                if search_res and gemini_quota_fails < QUOTA_FAIL_LIMIT:
                    extr = gemini_extract(search_res, gemini_key, "linkedin")
                    if extr:
                        gemini_quota_fails = 0
                    else:
                        gemini_quota_fails += 1

                    if extr and "linkedin.com" in extr:
                        linkedin = extr
                        print(f"  -> LinkedIn found: {linkedin}")
                    else:
                        print(f"  -> No LinkedIn extracted.")
                elif gemini_quota_fails >= QUOTA_FAIL_LIMIT:
                    print("  [quota-guard] Gemini quota exhausted — skipping extraction")

        # ── Email search ────────────────────────────────────────────────────
        if ("email" in missing or missing == "both") and not email:
            if tavily_quota_fails >= QUOTA_FAIL_LIMIT:
                print("  [quota-guard] Tavily quota exhausted — skipping email search")
            else:
                domain = (
                    row.get("Link", "")
                    .replace("https://", "").replace("http://", "")
                    .replace("www.", "").strip("/ ")
                )
                q = (
                    f'"{contact}" email "@"{domain} contact'
                    if contact and domain
                    else f'"{company}" contact email address'
                )
                search_res = tavily_search(q, tavily_key)
                if search_res:
                    tavily_quota_fails = 0
                else:
                    tavily_quota_fails += 1

                if search_res and gemini_quota_fails < QUOTA_FAIL_LIMIT:
                    extr = gemini_extract(search_res, gemini_key, "email")
                    if extr:
                        gemini_quota_fails = 0
                    else:
                        gemini_quota_fails += 1

                    if extr and "@" in extr:
                        email = extr
                        print(f"  -> Email found: {email}")
                    else:
                        print(f"  -> No email extracted.")
                elif gemini_quota_fails >= QUOTA_FAIL_LIMIT:
                    print("  [quota-guard] Gemini quota exhausted — skipping extraction")

        # ── Update row ──────────────────────────────────────────────────────
        row["Linkedin"] = linkedin
        row["Email"]    = email

        gaps = []
        if not email:    gaps.append("email_missing")
        if not linkedin: gaps.append("linkedin_missing")
        row["missing_data"] = (
            "both" if len(gaps) == 2
            else gaps[0] if len(gaps) == 1
            else ""
        )

        # Incremental save after each lead so partial runs aren't lost
        with open(INPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        time.sleep(1)

    print("\n✅ Enrichment pass complete.")
    print(f"   Tavily quota failures: {tavily_quota_fails}")
    print(f"   Gemini quota failures: {gemini_quota_fails}")


if __name__ == "__main__":
    main()
