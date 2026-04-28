"""
Notification store — persists reply notifications in notif.json.
Read state resets on redeploy (acceptable for free tier ephemeral fs).
IMAP is re-polled on each startup so replies are always recoverable.
"""

import json
import threading
import time
from pathlib import Path

_DIR        = Path(__file__).parent
_NOTIF_FILE = _DIR / "notif.json"
_lock       = threading.Lock()

_last_check: float = 0.0
_CHECK_INTERVAL    = 300.0  # 5 minutes


# ── Persistence ───────────────────────────────────────────────────────────────

def load_notifications() -> list[dict]:
    if not _NOTIF_FILE.exists():
        return []
    try:
        with _lock:
            return json.loads(_NOTIF_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_notifications(notifs: list[dict]) -> None:
    with _lock:
        _NOTIF_FILE.write_text(
            json.dumps(notifs, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# ── Read state ────────────────────────────────────────────────────────────────

def get_unread_count() -> int:
    return sum(1 for n in load_notifications() if not n.get("read"))


def mark_read(notif_id: str) -> None:
    notifs = load_notifications()
    for n in notifs:
        if n["id"] == notif_id:
            n["read"] = True
            break
    save_notifications(notifs)


def mark_all_read() -> None:
    notifs = load_notifications()
    for n in notifs:
        n["read"] = True
    save_notifications(notifs)


# ── Merge ─────────────────────────────────────────────────────────────────────

def merge_replies(new_replies: list[dict]) -> int:
    """Insert truly new replies at front. Returns count added."""
    existing     = load_notifications()
    existing_ids = {n["id"] for n in existing}
    added = 0
    for r in new_replies:
        if r["id"] not in existing_ids:
            existing.insert(0, r)
            added += 1
    if added:
        save_notifications(existing)
    return added


# ── Poll throttle ─────────────────────────────────────────────────────────────

def should_check() -> bool:
    return (time.monotonic() - _last_check) > _CHECK_INTERVAL


def record_check() -> None:
    global _last_check
    _last_check = time.monotonic()
