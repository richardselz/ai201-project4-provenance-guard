"""Structured JSON audit log for Provenance Guard.

Every attribution decision and every appeal is appended to a single JSON file
as one entry object. Entries are distinguished by their `event_type` field
("classification" or "appeal") so submissions and appeals share one log but
stay easy to tell apart.
"""

import json
import os
from datetime import datetime, timezone

LOG_PATH = os.path.join(os.path.dirname(__file__), "audit_log.json")


def _now_iso():
    """Current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def read_log():
    """Return the full log as a list of entry dicts (empty list if none yet)."""
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            # A corrupt/empty file shouldn't crash the app; start fresh.
            return []


def append_entry(entry):
    """Append one entry dict to the log, stamping it with a timestamp.

    Returns the stored entry (with the timestamp added).
    """
    entry.setdefault("timestamp", _now_iso())
    log = read_log()
    log.append(entry)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)
    return entry


def get_recent(limit=20):
    """Return the most recent `limit` entries, newest last."""
    log = read_log()
    return log[-limit:]


def find_by_content_id(content_id):
    """Return the most recent classification entry for a content_id, or None.

    Used by the appeal flow (M5) to look up the original decision.
    """
    for entry in reversed(read_log()):
        if entry.get("content_id") == content_id and entry.get("event_type") == "classification":
            return entry
    return None
