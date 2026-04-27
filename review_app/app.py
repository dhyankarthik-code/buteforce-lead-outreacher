"""
Buteforce Outreach Review App
==============================
FastAPI server — serves the review UI and exposes the API.

Endpoints:
  GET  /                        → Review UI (index.html)
  GET  /api/queue               → Full queue + stats
  GET  /api/queue/{id}          → Single lead detail
  POST /api/generate/{id}       → Generate email via Gemini
  PUT  /api/queue/{id}          → Update subject/body/notes
  POST /api/send/{id}           → Send email + mark sent
  POST /api/skip/{id}           → Mark skipped
  POST /api/reset/{id}          → Reset to pending (re-generate)
"""

import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Load .env from this directory
load_dotenv(Path(__file__).parent / ".env")

from generator import generate_email
from mailer    import send_email

if os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
    from sheets_store import (
        init_queue, load_queue, get_item,
        update_item, mark_sent, queue_stats,
    )
else:
    from queue_store import (
        init_queue, load_queue, get_item,
        update_item, mark_sent, queue_stats,
    )

app = FastAPI(title="Buteforce Outreach Review")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

TEMPLATE = Path(__file__).parent / "templates" / "index.html"


# ── HTML ──────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def serve_ui():
    return TEMPLATE.read_text(encoding="utf-8")


# ── Queue ─────────────────────────────────────────────────────────────────────

@app.get("/api/queue")
def get_queue():
    queue = init_queue()
    return {"stats": queue_stats(queue), "queue": queue}


@app.get("/api/queue/{item_id}")
def get_lead(item_id: str):
    item = get_item(item_id)
    if not item:
        raise HTTPException(404, f"Lead {item_id} not found")
    return item


# ── Generate ──────────────────────────────────────────────────────────────────

@app.post("/api/generate/{item_id}")
def api_generate(item_id: str):
    item = get_item(item_id)
    if not item:
        raise HTTPException(404, f"Lead {item_id} not found")
    if not item.get("email"):
        raise HTTPException(400, "No email address for this lead — enrich first")

    try:
        result = generate_email(item)
    except RuntimeError as exc:
        raise HTTPException(500, str(exc))
    except Exception as exc:
        raise HTTPException(500, f"Generation failed: {exc}")

    updated = update_item(item_id, {
        "status":       "generated",
        "subject":      result["subject"],
        "body":         result["body"],
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    return updated


# ── Update (edit subject/body/notes) ──────────────────────────────────────────

class EmailUpdate(BaseModel):
    subject: str | None = None
    body:    str | None = None
    notes:   str | None = None


@app.put("/api/queue/{item_id}")
def api_update(item_id: str, payload: EmailUpdate):
    item = get_item(item_id)
    if not item:
        raise HTTPException(404, f"Lead {item_id} not found")

    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "Nothing to update")

    return update_item(item_id, updates)


# ── Send ──────────────────────────────────────────────────────────────────────

@app.post("/api/send/{item_id}")
def api_send(item_id: str):
    item = get_item(item_id)
    if not item:
        raise HTTPException(404, f"Lead {item_id} not found")
    if not item.get("email"):
        raise HTTPException(400, "No email address — enrich first")
    if not item.get("subject") or not item.get("body"):
        raise HTTPException(400, "Generate the email first before sending")
    if item.get("status") == "sent":
        raise HTTPException(400, "Already sent")

    success, error = send_email(item["email"], item["subject"], item["body"])

    if not success:
        raise HTTPException(500, f"Send failed: {error}")

    updated = mark_sent(item_id, item["subject"], item["body"])
    return {"ok": True, "item": updated}


# ── Skip ──────────────────────────────────────────────────────────────────────

@app.post("/api/skip/{item_id}")
def api_skip(item_id: str):
    item = get_item(item_id)
    if not item:
        raise HTTPException(404, f"Lead {item_id} not found")
    updated = update_item(item_id, {"status": "skipped"})
    return updated


# ── Reset ─────────────────────────────────────────────────────────────────────

@app.post("/api/reset/{item_id}")
def api_reset(item_id: str):
    item = get_item(item_id)
    if not item:
        raise HTTPException(404, f"Lead {item_id} not found")
    if item.get("status") == "sent":
        raise HTTPException(400, "Cannot reset a sent email")
    updated = update_item(item_id, {
        "status": "pending", "subject": "", "body": "",
        "generated_at": None, "notes": "",
    })
    return updated


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8765"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
