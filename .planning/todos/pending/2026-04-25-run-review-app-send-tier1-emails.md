---
created: 2026-04-25T00:00
title: Run review app and send Tier 1 outreach emails
area: tooling
files:
  - review_app/mailer.py
  - review_app/queue_store.py
  - start_review.bat
  - tier1_outreach_emails.md
  - outreach_tracker.csv
---

## Problem

Six Tier 1 cold emails have been written and stored in `tier1_outreach_emails.md`, and the
human-in-the-loop review app (`review_app/`) is fully built. However, nothing has actually
been sent yet — all rows in `outreach_tracker.csv` are blank.

The review app loads Tier 1 leads from `leads_clean.csv` into `review_app/queue.json`,
lets the operator review/edit each email, and sends via `mailer.py`. It is started with
`start_review.bat`.

Leads with written emails ready to send (in order of spend):
1. OneMagnify — securityteam@onemagnify.com ($8.4M)
2. Good to Great Schools AU — info@goodtogreatschools.org.au ($3.6M)
3. care.coach — hello@care.coach ($538K)
4. Simpalm — contact@simpalm.com ($395K)
5. CannabisTrainingUniversity — Support@thectu.com ($385K)
6. Chekin — support@chekin.com ($367K) ⚠️ GDPR — must populate [unsubscribe_link] before sending

LinkedIn-only leads (no email, use LinkedIn message instead):
- Christopher Jenkin (Gotcha! Mobile Solutions) — linkedin.com/in/christopherjenkin
- Quilen (Southside Blooms) — linkedin.com/company/southside-blooms

## Solution

1. Run `start_review.bat` to launch the review app
2. Check SMTP credentials are set in `review_app/.env` (Google Workspace SMTP via Brevo relay)
3. For Chekin: populate `[unsubscribe_link]` with a real Brevo unsubscribe URL before sending
4. Review + send each email one by one (max 10–15/day for Tier 1)
5. After sending, verify `outreach_tracker.csv` rows are updated with `email1_sent` timestamp
6. Send LinkedIn connection messages manually for Christopher Jenkin and Quilen
