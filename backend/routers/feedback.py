"""
/api/feedback — records thumbs up/down on assistant messages.

The frontend sends:
  POST /api/feedback
  {
    "messageId": "...",
    "type": "up" | "down",
    "text": "..."
  }

Feedback is appended to a JSONL file so it can be reviewed or replayed into
future fine-tuning/retraining passes. GET /api/feedback/stats returns real
aggregate counts computed from that file (no fabricated numbers).
"""

import json
import os
import time
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import verify_reviewer_key
import corrections_store

router = APIRouter()

_DATA_DIR = Path(os.getenv("FEEDBACK_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
_FEEDBACK_FILE = _DATA_DIR / "feedback.jsonl"


class FeedbackRequest(BaseModel):
    messageId: str = Field(..., max_length=128)
    type: str = Field(..., pattern=r"^(up|down)$")
    text: str = Field("", max_length=8_000)
    correction: str = Field("", max_length=4_000)


class ReviewRequest(BaseModel):
    action: Literal["approve", "reject"]


@router.post("/feedback")
async def record_feedback(req: FeedbackRequest):
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "messageId": req.messageId,
        "type": req.type,
        "text": req.text,
        "timestamp": time.time(),
    }
    with open(_FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    if req.correction.strip():
        corrections_store.add_correction(req.messageId, req.text, req.correction.strip())

    return {"status": "recorded"}


@router.get("/corrections", dependencies=[Depends(verify_reviewer_key)])
async def get_corrections(status: Literal["pending", "approved", "rejected"] | None = None):
    return corrections_store.list_corrections(status)


@router.post("/corrections/{correction_id}/review", dependencies=[Depends(verify_reviewer_key)])
async def review_correction_endpoint(correction_id: str, req: ReviewRequest):
    updated = corrections_store.review_correction(correction_id, req.action)
    if updated is None:
        raise HTTPException(status_code=404, detail="Correction not found")
    return updated


@router.get("/feedback/stats")
async def feedback_stats():
    if not _FEEDBACK_FILE.exists():
        return {"up": 0, "down": 0, "total": 0}

    up = down = 0
    with open(_FEEDBACK_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry.get("type") == "up":
                up += 1
            elif entry.get("type") == "down":
                down += 1

    return {"up": up, "down": down, "total": up + down}
