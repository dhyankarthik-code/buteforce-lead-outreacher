"""
Company researcher — Tavily search + Gemini Flash synthesis.
Builds a structured company intel brief before email generation.

Returns {} gracefully when TAVILY_API_KEY is not configured so the
rest of the pipeline continues without research.
"""

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

# Fallback: try reading TAVILY_API_KEY from the sibling marketing swarm project
_FALLBACK_ENV = (
    Path(__file__).parent.parent
    / "Marketing agents"
    / "buteforce-marketing-swarm"
    / ".env"
)

_MAX_RETRIES = 2
_BACKOFF_SEC = 3


def _get_tavily_key() -> str | None:
    key = os.environ.get("TAVILY_API_KEY")
    if key:
        return key
    if _FALLBACK_ENV.exists():
        try:
            with open(_FALLBACK_ENV, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("TAVILY_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip("'\"")
                        if val and "your-" not in val:
                            return val
        except OSError:
            pass
    return None


def _get_gemini_key() -> str | None:
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_AI_API_KEY"):
        key = os.environ.get(name)
        if key:
            return key
    return None


def _http_post(url: str, payload: dict, headers: dict) -> dict | None:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers)
    for attempt in range(_MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(_BACKOFF_SEC * (2 ** attempt))
            else:
                return None
        except Exception:
            return None
    return None


def _tavily_search(query: str, api_key: str) -> list[dict]:
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "advanced",
        "max_results": 4,
        "include_answer": True,
    }
    res = _http_post(
        "https://api.tavily.com/search",
        payload,
        {"Content-Type": "application/json"},
    )
    return (res or {}).get("results", [])


def _format_snippets(results: list[dict]) -> str:
    parts = []
    for r in results:
        title = r.get("title", "")
        url = r.get("url", "")
        content = (r.get("content") or "")[:500]
        parts.append(f"[{title}]\n{url}\n{content}")
    return "\n\n---\n\n".join(parts)


def _synthesize(snippets: str, company: str, gemini_key: str) -> dict:
    url = (
        "https://generativelanguage.googleapis.com/v1beta"
        f"/models/gemini-2.0-flash:generateContent?key={gemini_key}"
    )
    prompt = (
        f'You are a B2B sales research analyst briefing an AI dev agency on "{company}".\n\n'
        "Based on the search results below, return a JSON object with these exact keys:\n"
        "{\n"
        '  "company_overview": "2-3 sentences on what this company does and their target market",\n'
        '  "what_they_build": "specific products, platforms, apps or systems they build",\n'
        '  "tech_stack": "technologies, frameworks, AI/ML tools they use",\n'
        '  "recent_signals": "recent news, funding, product launches, or hiring signals (empty string if none found)",\n'
        '  "pain_points": "likely engineering or AI challenges inferred from their projects and stage",\n'
        '  "hook_angles": "2-3 specific non-obvious observations that could open a cold email — reference actual data points or product decisions, never generic compliments"\n'
        "}\n\n"
        "Return ONLY valid JSON. No markdown fences, no explanation.\n\n"
        f'Search results for "{company}":\n{snippets[:3500]}'
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 900,
            "response_mime_type": "application/json",
        },
    }
    res = _http_post(url, payload, {"Content-Type": "application/json"})
    if not res:
        return {}
    try:
        raw = res["candidates"][0]["content"]["parts"][0]["text"].strip()
        return json.loads(raw)
    except (KeyError, IndexError, json.JSONDecodeError):
        return {}


def research_company(lead: dict) -> dict:
    """
    Research a company via Tavily + Gemini Flash synthesis.

    Searches for company overview, tech stack, recent news, and LinkedIn presence,
    then synthesises into a structured brief that feeds the email generator.

    Returns {} gracefully if TAVILY_API_KEY is not configured.
    """
    tavily_key = _get_tavily_key()
    if not tavily_key:
        return {}

    company = (lead.get("company") or "").strip()
    if not company:
        return {}

    project = (lead.get("project_name") or "").strip()
    queries = [
        f"{company} company products services what do they build",
        f"{company} technology stack AI machine learning engineering",
        f"{company} news funding startup growth 2024 2025",
        f"{company} {project}" if project else f'"{company}" site:linkedin.com/company',
    ]

    all_results: list[dict] = []
    seen_urls: set[str] = set()
    for query in queries:
        for r in _tavily_search(query, tavily_key):
            u = r.get("url", "")
            if u and u not in seen_urls:
                seen_urls.add(u)
                all_results.append(r)
        time.sleep(0.4)

    if not all_results:
        return {}

    snippets = _format_snippets(all_results[:12])
    gemini_key = _get_gemini_key()
    if not gemini_key:
        return {"sources_count": len(all_results)}

    brief = _synthesize(snippets, company, gemini_key)
    brief["sources_count"] = len(all_results)
    return brief
