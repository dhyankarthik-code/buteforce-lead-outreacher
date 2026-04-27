# PROJECT HANDOFF — Buteforce Outreach & Lead Intelligence System
**Written:** 2026-04-06 | **Status:** Ready for new agent handoff  
**Files to copy into the new project dir alongside this doc:**
- `Name sheet - Clients data.csv` ← the lead dataset

---

## 1. Who Buteforce Is

**Buteforce** is a technology agency/studio that positions itself as an enterprise-grade alternative to unreliable freelance work, branding itself around the concept of "Architectural Intelligence."

- **Website:** Live on Vercel (Next.js 15, React 19, Tailwind CSS)
- **Core Services:** AI engineering, voice agents, RAG systems, LangChain/N8N automation, full-stack AI builds, web development
- **Brand Tone:** Premium, technical, authoritative — NOT a freelancer, NOT a generic dev shop
- **Analytics/GTM:** Google Tag Manager `GTM-PZN4P56H`, Google Analytics `G-T3LTVKY35T` are live
- **SEO Status:** Fully optimized with JSON-LD schemas (Organization, FAQPage, Service, Article), `robots.txt` tuned for AI bots, `llms.txt` + `llms-full.txt` for GEO (Generative Engine Optimization), `og-image.png` deployed

---

## 2. What This New Project Is

This is a **standalone outreach & lead intelligence system** — completely separate from the main website codebase. The goal:

> Transform a manually scraped CSV of 77 Upwork leads into an active outreach pipeline that converts high-value clients into Buteforce engagements.

This project lives in its own directory. It does NOT modify the `buteforce-website/` codebase in any way.

---

## 3. The Lead Dataset — `Name sheet - Clients data.csv`

### What it is
77 manually scraped Upwork client records collected over ~6 months. Columns:
`S. No, Company Name, Contact Name, Mobile, Company's Country, Email, Link (company website), Linkedin, Name of the REF. (freelancer who won the job), Awarded to Freelancers Country, Spent, Job type, Project Name, Job Link`

### Key stats
| Metric | Value |
|---|---|
| Total valid leads | 77 (rows 78–184 are blank, to be deleted) |
| Primary interest | AI (Voice Agents, RAG, LangChain, N8N, LLMs) ~80% |
| Secondary interest | Web Dev ~20% |
| Spend range | $2.2K → $700K+ |
| Top geographies | USA, Australia, UK, Canada, EU (Belgium, Spain, Greece) |
| Data quality issues | ~15–20% missing email or LinkedIn; some phone numbers in non-standard format |

### Lead Tiers (by Spend)
| Tier | Spend | Est. Count | Approach |
|---|---|---|---|
| Tier 1 | $200K–$700K+ | ~12 | Manual, hyper-personalized outreach only |
| Tier 2 | $50K–$200K | ~25 | Semi-automated via Marketing Swarm (AdK) |
| Tier 3 | $2K–$50K | ~40 | Fully automated swarm sequences |

### Tier 1 Priority Leads (Hand-craft these first)
| Company | Contact | Spend | Job Type | Email |
|---|---|---|---|---|
| Southside Blooms | Quilen | $700K+ | AI Smart Router | (missing — enrich) |
| OneMagnify | — | $8.4M | AI Engineer (LT) | securityteam@onemagnify.com |
| Good to Great Schools AU | — | $3.6M | Web Dev (Backend) | info@goodtogreatschools.org.au |
| Fu Dog Media | Ben Capa | $1M | AI Specialist | (missing — enrich) |
| Gotcha! Mobile Solutions | Christopher Jenkin (CEO) | $1.6M | Senior AI Dev | (missing — LinkedIn: linkedin.com/in/christopherjenkin) |
| Evolved Office | Marc | $500K+ | AI Deep Tool Dev | dealersolutions@evolvedoffice.com |
| Investabill | Vineetha | $500K+ | RAG AI Bot | yield@investabill.com |
| care.coach | — | $538K | AI/ML Engineer | hello@care.coach |
| Chekin | Carlos | $367K | Voice AI Agent | support@chekin.com |
| OMG Marketing | Joseph Lopez (CEO) | $381K | AI Automation | joseph@omgmarketingco.com |
| CannabisTrainingUniversity | Jeff Zorn (CEO) | $385K | Web Dev | Support@thectu.com |
| Simpalm | Vikram | $395K | AI (n8n/LangChain) | contact@simpalm.com |

> ⚠️ OneMagnify ($8.4M) and Good to Great Schools ($3.6M) are enterprise orgs. Pitch as an agency, not a service provider.

---

## 4. The Marketing Infrastructure (Already Built — Separate Repo)

Buteforce has an existing **Marketing Swarm** built on **Google's Agentic Development Kit (AdK)**. It is a separate project/repo (location not in this dir). The new agent should be aware:

- The Swarm handles automated multi-channel outreach sequences
- It can ingest structured CSV/JSON lead data
- Tier 2 and Tier 3 leads should be fed into this Swarm after the CSV is cleaned
- Tier 1 leads should **NOT** go through the Swarm — they get manual, human-written outreach

---

## 5. The Outreach Strategy (What's Been Decided)

### The Core Angle
These leads hired freelancers for AI/Web Dev on Upwork. They are **problem-aware** and **solution-aware**. The pitch is: Buteforce is the enterprise-grade agency alternative with accountability, architecture thinking, and no single-point-of-failure.

### The Hook — "AI Audit" Conversion Funnel
Buteforce has a live **AI Audit landing page**. The playbook:
1. Warm the lead (LinkedIn connect + check-in email referencing their Upwork project)
2. If they respond with friction → offer a free "Architectural AI Audit" of their existing system
3. Audit findings → upsell Buteforce retainer or rebuild engagement

### Segment-Specific Audit Hooks (Don't use a generic pitch)
| Lead Type | Hook |
|---|---|
| Voice AI / RAG | "We audit voice agent architectures for latency, failover, and prompt injection vulnerabilities." |
| N8N / LangChain | "We audit automation workflows for data leakage and webhook security exposures." |
| Computer Vision | "We review CV pipelines for model drift, edge case failures, and deployment bottlenecks." |
| Full-Stack AI | "We audit AI codebases for hardcoded keys, insecure endpoints, and scalability ceilings." |

### Multi-Channel Sequence (Marketing Swarm)
- **Day 1:** LinkedIn connection request — no pitch, just shared AI industry interest
- **Day 2:** Email 1 — The Check-In (reference their specific past Upwork project by name)
- **Day 5:** Email 2 — Value-add (a Buteforce case study or insight relevant to their job type)

### GDPR — Critical for EU Leads
EU endpoints (Belgium, Spain, UK, Greece, Ireland, Netherlands) require:
- Clear opt-out link in every email
- Legitimate interest justification documented
- Do NOT blast these with automated sequences without reviewing GDPR compliance first

---

## 6. What the New Agent Must Build (Task List)

### Step 0 — Python CSV Cleaner (Highest Priority)
Write a Python script that:
- Removes blank rows 78–184
- Parses the `Spent` column into a clean integer (remove `$`, `K`, `M`, `+` symbols)
- Adds a `tier` column (1/2/3) based on spend thresholds ($200K+ = 1, $50K–$200K = 2, below = 3)
- Adds a `missing_data` column flagging `email_missing`, `linkedin_missing`, or `both`
- Adds a `gdpr_flag` boolean column for EU-based leads
- Exports two outputs:
  - `leads_clean.csv` — cleaned flat file for Marketing Swarm ingestion
  - `leads_enrichment_needed.csv` — Tier 1 + Tier 2 leads with missing data for manual enrichment

### Step 1 — Data Enrichment (Manual)
For all Tier 1 leads with missing emails:
- Use Google operators: `site:linkedin.com/in/ "Name" "Company"`
- Use Hunter.io free tier or Apollo.io free tier
- Try standard B2B email formats: `first.last@company.com`, `first@company.com`
- Validate with a free SMTP checker before use

### Step 2 — Secondary Domain Setup
Buteforce must NOT send cold email from `buteforce.com` — it risks damaging SEO/sending reputation.
- Register a variation domain (e.g., `buteforce.io`, `buteforceagency.com`, `getbuteforce.com`)
- Configure SPF, DKIM, DMARC records on it
- All cold outreach goes from this domain only

### Step 3 — Campaign Execution
- Tier 1: Manual outreach, human-written, one at a time
- Tier 2 & 3: Feed `leads_clean.csv` into the Marketing Swarm AdK project

---

## 7. Open Questions The New Agent Should Ask the User

1. **Secondary domain** — Does the user own any Buteforce domain variation other than `.com`?
2. **Marketing Swarm location** — Where is the AdK Marketing Swarm project directory on this machine? The new agent will need to reference it for Tier 2/3 ingestion.
3. **Email sending tool** — What SMTP/sending service is planned? (e.g., Instantly.ai, Lemlist, Mailgun on secondary domain?)
4. **LinkedIn outreach** — Will this be manual, or is a tool like Dux-Soup or PhantomBuster being considered?

---

## 8. Note on Obsidian (Gracefully Dropped)

The previous strategy session considered Obsidian as a local CRM. **Decision: Drop it.** Reason: The Python script + a clean CSV is sufficient for the Marketing Swarm to ingest. Obsidian adds setup overhead without providing automation value. A simple spreadsheet or the CSV itself is the right "CRM" at this stage. Obsidian is a great tool for personal knowledge management, but this project needs pipeline automation, not note-taking.

> ✅ Obsidian works perfectly fine on a laptop that gets switched off — it is a local desktop app with no background service required. All data is plain markdown files, nothing is lost when you shut down. **But it's not needed here**, so we're passing on it.

---

*End of handoff. The new agent should start with Step 0 (Python CSV cleaner) and the four open questions above.*
