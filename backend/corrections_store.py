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
import threading
import time
import uuid
from pathlib import Path
from typing import Literal

_DATA_DIR = Path(os.getenv("FEEDBACK_DATA_DIR", Path(__file__).resolve().parent / "data"))
_CORRECTIONS_FILE = _DATA_DIR / "corrections.jsonl"

Status = Literal["pending", "approved", "rejected"]

# Guards the read-modify-write cycle in add_correction/review_correction against
# concurrent calls within this process (e.g. if either is ever moved onto a
# thread-pool executor). This does NOT protect against multiple OS processes
# (multiple uvicorn workers, or >1 Fly machine) writing the same file
# concurrently — the current deployment runs a single worker on a single
# machine, so that case doesn't arise today. See docs/deployment.md for the
# planned migration to a real datastore before scaling out.
_LOCK = threading.Lock()


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
    """Write the full entry list atomically: write to a temp file in the same
    directory, then os.replace() over the real file. Without this, a process
    kill/crash (OOM, deploy restart) mid-write on the old direct-write path
    could truncate corrections.jsonl and silently lose every prior entry —
    not just the one being written."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = _CORRECTIONS_FILE.with_suffix(f".jsonl.tmp-{uuid.uuid4().hex}")
    with open(tmp_path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, _CORRECTIONS_FILE)


def add_correction(
    message_id: str,
    original_text: str,
    correction: str,
    contributor_id: str | None = None,
) -> dict:
    entry = {
        "id": uuid.uuid4().hex,
        "messageId": message_id,
        "originalText": original_text,
        "correction": correction,
        "contributorId": contributor_id,
        "status": "pending",
        "timestamp": time.time(),
        "reviewedAt": None,
        "reviewedBy": None,
    }
    with _LOCK:
        entries = _read_all()
        entries.append(entry)
        _write_all(entries)
    return entry


def list_corrections(status: Status | None = None) -> list[dict]:
    entries = _read_all()
    if status is None:
        return entries
    return [e for e in entries if e.get("status") == status]


def review_correction(
    correction_id: str, action: Literal["approve", "reject"], reviewed_by: str
) -> dict | None:
    with _LOCK:
        entries = _read_all()
        updated = None
        for e in entries:
            if e["id"] == correction_id:
                e["status"] = "approved" if action == "approve" else "rejected"
                e["reviewedAt"] = time.time()
                e["reviewedBy"] = reviewed_by
                updated = e
                break
        if updated is not None:
            _write_all(entries)
    return updated


def _sanitize_for_prompt(text: str) -> str:
    """Strip bracket-tag-shaped structure and hard newlines before splicing
    user-submitted text into the shared system prompt.

    Corrections are the one channel in this codebase where one user's
    submitted text can change model behavior for every OTHER user (see
    module docstring) — the human-review gate is real mitigation, but a
    plausible-sounding, mistakenly-approved submission containing literal
    "[HUMAN_VALIDATED_CORRECTIONS]:" or "[CORRECTION]:" text (or embedded
    newlines shaping fake structure) could otherwise forge additional fake
    correction entries once rendered, on top of whatever the reviewer
    actually approved. Found in the 2026-08-23 follow-up security-
    architecture review."""
    return text.replace("[", "(").replace("]", ")").replace("\n", " ").replace("\r", " ")


def get_approved_corrections_prompt() -> str:
    """Rendered as extra system-prompt content — this is how approved
    corrections actually change model behavior, for every user, immediately."""
    approved = list_corrections("approved")
    if not approved:
        return ""
    lines = [
        f"[CORRECTION]: When asked something like '{_sanitize_for_prompt(e['originalText'])}', "
        f"the verified correct answer is: '{_sanitize_for_prompt(e['correction'])}'"
        for e in approved
    ]
    return "[HUMAN_VALIDATED_CORRECTIONS]:\n" + "\n".join(lines)
