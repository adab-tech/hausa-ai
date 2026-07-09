"""
Human-validated correction pipeline.

When a user marks a response as wrong, they may submit what the correct
answer should have been. That correction is NOT applied automatically —
it sits in a pending queue until a reviewer (the project owner, or anyone
they delegate via REVIEWER_API_KEY) approves it. Only approved corrections
get folded into the system prompt via get_approved_corrections_prompt(),
which chat.py calls on every request.

This is the gate that keeps the model learning from real usage without
being poisoned by bad-faith or mistaken submissions.
"""

import json
import os
import time
import uuid
from pathlib import Path
from typing import Literal

_DATA_DIR = Path(os.getenv("FEEDBACK_DATA_DIR", Path(__file__).resolve().parent / "data"))
_CORRECTIONS_FILE = _DATA_DIR / "corrections.jsonl"

Status = Literal["pending", "approved", "rejected"]


def _read_all() -> list[dict]:
    if not _CORRECTIONS_FILE.exists():
        return []
    entries = []
    with open(_CORRECTIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def _write_all(entries: list[dict]) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(_CORRECTIONS_FILE, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def add_correction(message_id: str, original_text: str, correction: str) -> dict:
    entry = {
        "id": uuid.uuid4().hex,
        "messageId": message_id,
        "originalText": original_text,
        "correction": correction,
        "status": "pending",
        "timestamp": time.time(),
        "reviewedAt": None,
    }
    entries = _read_all()
    entries.append(entry)
    _write_all(entries)
    return entry


def list_corrections(status: Status | None = None) -> list[dict]:
    entries = _read_all()
    if status is None:
        return entries
    return [e for e in entries if e.get("status") == status]


def review_correction(correction_id: str, action: Literal["approve", "reject"]) -> dict | None:
    entries = _read_all()
    updated = None
    for e in entries:
        if e["id"] == correction_id:
            e["status"] = "approved" if action == "approve" else "rejected"
            e["reviewedAt"] = time.time()
            updated = e
            break
    if updated is not None:
        _write_all(entries)
    return updated


def get_approved_corrections_prompt() -> str:
    """Rendered as extra system-prompt content — this is how approved
    corrections actually change model behavior, for every user, immediately."""
    approved = list_corrections("approved")
    if not approved:
        return ""
    lines = [
        f"[CORRECTION]: When asked something like '{e['originalText']}', "
        f"the verified correct answer is: '{e['correction']}'"
        for e in approved
    ]
    return "[HUMAN_VALIDATED_CORRECTIONS]:\n" + "\n".join(lines)
