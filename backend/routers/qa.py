"""
Community Hausa Q&A — native-written instruction data for the LLM training mix.

PUBLIC (native speakers):
  POST /api/qa/submit                 — submit a Hausa question + answer (pending)

ADMIN (owner gate, verify_admin_session):
  GET    /api/admin/qa                 — list (optional ?status=) + counts
  POST   /api/admin/qa/{id}/status     — approve / reject
  DELETE /api/admin/qa/{id}            — remove
  GET    /api/admin/qa/export          — approved pairs as instruction JSONL

Nothing enters the training mix without approval — same gate as pronunciation.
"""

import io
import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

import qa_store as store
from auth import verify_admin_session, verify_csrf_origin
from contributor import get_contributor_id
from rate_limit import limiter

router = APIRouter()


class QABody(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)
    answer: str = Field(..., min_length=2, max_length=4000)
    topic: str | None = Field(None, max_length=80)


@router.post("/qa/submit")
@limiter.limit("10/minute")
async def submit_qa(request: Request, body: QABody):
    """PUBLIC: a native speaker contributes a Hausa Q&A pair. Lands 'pending' —
    the owner approves before it ever enters the training data."""
    row_id = store.submit(
        question=body.question, answer=body.answer, topic=body.topic,
        submitted_by=get_contributor_id(request),
    )
    if row_id is None:
        raise HTTPException(status_code=400, detail="Question and answer required")
    return {"ok": True, "id": row_id}


@router.get("/admin/qa")
async def admin_list(status: str | None = None, _admin: str = Depends(verify_admin_session)):
    return {"items": store.list_items(status=status), "counts": store.counts()}


class StatusBody(BaseModel):
    status: str = Field(..., pattern=r"^(pending|approved|rejected)$")


@router.post("/admin/qa/{row_id}/status", dependencies=[Depends(verify_csrf_origin)])
async def admin_status(row_id: int, body: StatusBody, _admin: str = Depends(verify_admin_session)):
    if not store.set_status(row_id, body.status):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True, "id": row_id, "status": body.status}


@router.delete("/admin/qa/{row_id}", dependencies=[Depends(verify_csrf_origin)])
async def admin_delete(row_id: int, _admin: str = Depends(verify_admin_session)):
    if not store.delete(row_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True, "id": row_id}


@router.get("/admin/qa/export")
async def admin_export(_admin: str = Depends(verify_admin_session)):
    """Download approved Q&A as instruction JSONL for the training mix."""
    rows = store.export_approved()
    if not rows:
        raise HTTPException(status_code=404, detail="No approved Q&A to export yet")
    buf = io.StringIO()
    for r in rows:
        buf.write(json.dumps(r, ensure_ascii=False) + "\n")
    return Response(
        content=buf.getvalue(),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": "attachment; filename=murya_community_qa.jsonl"},
    )
