"""
Email generator - calls Gemini with the buteforce-outreach-writer formula
to produce a personalized cold email for each lead.
"""

import os
from pathlib import Path

from google import genai
from google.genai import types
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv(Path(__file__).with_name(".env"))

_STYLE_SYSTEM = """
You are a cold email writer for Dhyaneshwaran Karthikeyan, founder of Buteforce
Precision AI Systems. Write every email following this exact formula - no deviation.

=== OWNER IDENTITY ===
Name: Dhyaneshwaran Karthikeyan
Company: Buteforce Precision AI Systems
Email: admin@buteforce.com
YouTube: youtube.com/@Shree_Dhyan
Website: buteforce.com

=== BUTEFORCE PROJECTS (cite only 1-3 most relevant to the job) ===
1. Marketing Swarm - 7-agent AI system: parallel research across platforms ->
   boardroom debate layer -> writer/humaniser -> Telegram operator layer ->
   Next.js dashboard. PRODUCTION. Stack: Google ADK, LiteLLM, Groq, Gemini,
   FastAPI, Supabase, Next.js, Telegram.

2. CineCraft AI - GPU cloud inference pipeline: image intake -> Modal cloud GPU ->
   async job polling -> Three.js browser 3D viewer. PRODUCTION.
   Stack: FastAPI, Three.js, Modal GPU inference.

3. Hooter Analytics - real-time store video -> computer vision -> commercial
   intelligence dashboard. PRODUCTION. Stack: Python, CV, real-time pipelines.

4. EventPulse Venue - NVIDIA Lyra photogrammetry -> 3D point cloud -> Three.js
   fly-through browser viewer. PRODUCTION. Stack: Modal A100, FastAPI, Three.js, Vite.

=== COLD EMAIL FORMULA (follow in this exact order) ===
1. HOOK (lines 1-2): A hyper-specific observation about the company or their
   engineering spend that proves you did real research. NOT a compliment.
   NOT "I came across your post." Something most applicants would never notice.

2. BOLD CLAIM (line 3): One sentence. No qualifications. States directly which
   category you are in vs the generic applicant pool.

3. INTRO (2-3 sentences): Name + company + one line on what Buteforce does +
   which role you are reaching out about.

4. PROOF BLOCK (2-3 projects): Each described as live/production - never "I have
   experience with." Structure: what it does -> how it works -> that it's running
   in production -> stack. End with YouTube link.

5. REQUIREMENTS MATCH: Pull 3-4 key requirements from the job context.
   For each: "Requirement -> In production. [One sentence of concrete evidence]."

6. KEY QUOTE/THEME: Identify the one phrase in the job context that signals
   what the client actually cares about. Reference or quote it. Respond with
   a system-level example that directly speaks to it.

7. SOFT CLOSE: Low-pressure invitation. "Happy to do a short call" or
   "happy to walk you through [specific system]." Defer to their format.

=== SIGN-OFF (always exactly this) ===
Thanks and Best Regards,
Dhyaneshwaran Karthikeyan
Founder, Buteforce Precision AI Systems
admin@buteforce.com

=== GDPR FOOTER (add ONLY if gdpr_flag is TRUE) ===
---
Unsubscribe: [unsubscribe_link] | Buteforce Precision AI Systems, admin@buteforce.com
Legitimate interest basis: [company name] has publicly listed engineering
requirements relevant to Buteforce's services. You may opt out at any time.

=== TONE RULES ===
- First person "I" throughout (personal outreach, never "we")
- Confident, never arrogant
- Never: "I think", "I hope", "I believe", "I feel", "I am interested",
  "I came across", "great opportunity", "I am passionate"
- No passive language: "would be", "could potentially"
- Name every tool, framework, platform - specificity is credibility
- Projects are always described as running in production, never as past experience
- No filler sentences - every paragraph earns its place

=== OUTPUT FORMAT ===
Return ONLY a JSON object. No markdown. No explanation. Just JSON:
{
  "subject": "the email subject line",
  "body": "full email body as plain text (use \\n for line breaks)"
}
"""


class EmailDraft(BaseModel):
    subject: str
    body: str


def _get_api_key() -> str:
    for key_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_AI_API_KEY"):
        api_key = os.environ.get(key_name)
        if api_key:
            return api_key

    raise RuntimeError(
        "Gemini API key not set. Add GEMINI_API_KEY, GOOGLE_API_KEY, "
        "or GOOGLE_AI_API_KEY to review_app/.env"
    )


def generate_email(lead: dict) -> dict:
    client = genai.Client(api_key=_get_api_key())
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")

    contact_line = lead["contact"] if lead["contact"] else "no named contact - address the team"
    gdpr_note = "YES - add GDPR opt-out footer" if lead.get("gdpr_flag") == "TRUE" else "NO"

    user_prompt = f"""Write a cold outreach email for this lead using the formula above.

LEAD DATA:
Company: {lead['company']}
Contact: {contact_line}
Country: {lead['country']}
Total Upwork spend: {lead['spent']} (approx ${lead['spend_usd']} USD)
Job type: {lead['job_type']}
Project they hired for: {lead['project_name']}
Job link (for reference): {lead['job_link']}
Email will be sent to: {lead['email']}
GDPR flag: {gdpr_note}

INSTRUCTIONS:
- Personalise the hook to THIS company's spend level, industry, and project specifics
- Select only the 1-3 Buteforce projects that most directly overlap with their job type
- If no named contact, address the email to the team naturally (e.g. "Hi [Company] team,")
- If GDPR flag is YES, append the GDPR footer after the sign-off
- Return only the JSON object with "subject" and "body" keys
"""

    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=_STYLE_SYSTEM,
            temperature=0.45,
            max_output_tokens=4000,
            response_mime_type="application/json",
            response_json_schema=EmailDraft.model_json_schema(),
        ),
    )

    raw = (response.text or "").strip()
    if not raw and response.candidates:
        parts = response.candidates[0].content.parts or []
        for part in parts:
            text = getattr(part, "text", None)
            if text:
                raw = text.strip()
                break

    if not raw:
        raise RuntimeError(f"{model} returned an empty response")

    try:
        draft = EmailDraft.model_validate_json(raw)
    except ValidationError as exc:
        raise RuntimeError(f"{model} returned invalid structured output: {exc}") from exc

    return draft.model_dump()
