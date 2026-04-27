"""
Buteforce Lead Outreacher — Swarm Ingest (Step 4)
=================================================
Reads leads_clean.csv and pushes Tier 2 & Tier 3 rows 
into the Marketing Swarm's Supabase "campaigns" table.

Run:
  python ingest_leads.py
"""

import os
import csv
import json
import urllib.request
import urllib.error

# ── Config ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(SCRIPT_DIR, "leads_clean.csv")
ENV_FILE = os.path.join(SCRIPT_DIR, r"..\Marketing agents\buteforce-marketing-swarm\.env")

def load_env() -> dict:
    """Reads the .env file from the Swarm project manually to avoid external deps."""
    env_vars = {}
    if not os.path.exists(ENV_FILE):
        raise FileNotFoundError(f"Swarm .env not found at {ENV_FILE}")
        
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip().strip("'\"")
    return env_vars

def push_to_supabase(url: str, key: str, records: list[dict]):
    """Push records to Supabase REST API securely."""
    endpoint = f"{url}/rest/v1/campaigns"
    
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    req = urllib.request.Request(
        endpoint, 
        data=json.dumps(records).encode("utf-8"), 
        headers=headers,
        method="POST"
    )
    
    try:
        urllib.request.urlopen(req)
        return True
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code} {e.reason}")
        print(e.read().decode("utf-8"))
        return False
    except urllib.error.URLError as e:
        print(f"URLError: {e.reason}")
        return False

def main():
    print("Loading Swarm config...")
    env_vars = load_env()
    
    supabase_url = env_vars.get("SUPABASE_URL")
    supabase_key = env_vars.get("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL or SUPABASE_SERVICE_KEY missing in Swarm .env")
        return
        
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: {INPUT_FILE} not found. Run clean_leads.py first.")
        return

    print("Reading leads_clean.csv...")
    records_to_insert = []
    
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                tier = int(row.get("tier", 3))
            except ValueError:
                tier = 3
                
            # Filter: we only push Tier 2 & 3 to the automated Swarm.
            if tier == 1:
                continue
                
            company = row.get("Company Name", "Unknown Company").strip()
            project = row.get("Project Name", "Unknown Project").strip()
            
            # Pack all context into the owner_brief JSON block.
            brief_data = {
                "contact_name": row.get("Contact Name", ""),
                "email": row.get("Email", ""),
                "linkedin": row.get("Linkedin", ""),
                "mobile": row.get("Mobile", ""),
                "country": row.get("Company's Country", ""),
                "spent": row.get("Spent", ""),
                "tier": tier,
                "job_type": row.get("Job type", ""),
                "project_name": project,
                "job_link": row.get("Job Link", ""),
                "gdpr_flag": row.get("gdpr_flag", "FALSE")
            }
            
            record = {
                "title": company,
                "topic": f"Tier {tier} Lead Outreach - {job_type if (job_type := row.get('Job type')) else 'General'}",
                "owner_brief": json.dumps(brief_data, indent=2),
                "source": "csv_import",
                "status": "intake"
            }
            
            records_to_insert.append(record)

    if not records_to_insert:
        print("No Tier 2 or 3 leads found to push.")
        return
        
    print(f"Pushing {len(records_to_insert)} Tier 2/3 leads to the Marketing Swarm...")
    
    # We will slice into batches of 50 to avoid massive payloads
    batch_size = 50
    success = 0
    
    for i in range(0, len(records_to_insert), batch_size):
        batch = records_to_insert[i:i+batch_size]
        print(f"  Pushing batch {i//batch_size + 1} ({len(batch)} records)...")
        if push_to_supabase(supabase_url, supabase_key, batch):
             success += len(batch)
        else:
             print("  ❌ Batch failed.")
             
    print(f"\n✅ Done. Successfully pushed {success} out of {len(records_to_insert)} leads.")

if __name__ == "__main__":
    main()
