"""
MOS (Mean Opinion Score) listening test — naturalness eval for the TTS voice.

PUBLIC (listener, no login, anonymous):
  GET  /api/mos/session               — a randomized, blind 20-clip session
  GET  /api/mos/audio/{clip_id}       — one clip's audio (WAV)
  POST /api/mos/session               — submit a listener's ratings

ADMIN (self-gated via verify_admin_session):
  GET  /api/admin/mos/results         — aggregated stats + plain-language analysis
  GET  /api/admin/mos/export          — raw ratings as CSV

See mos_store.py for the storage/aggregation logic and why this exists
alongside the pronunciation-correction loop.
"""

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

import admin_audit_store
import mos_store as store
from auth import verify_admin_session, verify_csrf_origin
from contributor import get_contributor_id
from rate_limit import limiter

router = APIRouter()

_MAX_SESSION_ANSWERS = 40  # generous ceiling above the real session size (20)


@router.get("/mos/session")
@limiter.limit("20/minute")
async def get_session(request: Request):
    session = store.build_session()
    if not session:
        raise HTTPException(status_code=503, detail="No listening-test stimuli available yet")
    return {"clips": session}


@router.get("/mos/audio/{clip_id}")
@limiter.limit("120/minute")
async def get_audio(request: Request, clip_id: str):
    from routers.audio import _add_wav_header
    pcm = store.get_audio(clip_id)
    if not pcm:
        raise HTTPException(status_code=404, detail="Clip not found")
    return Response(content=_add_wav_header(pcm, sample_rate=24000), media_type="audio/wav")


class AnswerIn(BaseModel):
    clip_id: str = Field(..., max_length=80)
    condition: str = Field(..., pattern=r"^(murya|ground_truth)$")
    voice: str = Field(..., max_length=16)
    sentence_id: str = Field(..., max_length=16)
    score: int = Field(..., ge=1, le=5)
    intelligible: str = Field(..., pattern=r"^(yes|partial|no)$")
    replays: int = Field(0, ge=0, le=50)


class SessionSubmit(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    region: str | None = Field(None, max_length=64)
    native_speaker: bool = False
    answers: list[AnswerIn] = Field(..., min_length=1, max_length=_MAX_SESSION_ANSWERS)


@router.post("/mos/session")
@limiter.limit("6/minute")
async def submit_session(request: Request, body: SessionSubmit):
    answers = [
        store.RatingIn(
            clip_id=a.clip_id, condition=a.condition, voice=a.voice,
            sentence_id=a.sentence_id, score=a.score, intelligible=a.intelligible,
            replays=a.replays,
        )
        for a in body.answers
    ]
    n = store.record_session(
        session_id=body.session_id, answers=answers, region=body.region,
        native_speaker=body.native_speaker, submitted_by=get_contributor_id(request),
    )
    return {"ok": True, "recorded": n}


@router.get("/admin/mos/results")
async def admin_results(_admin: str = Depends(verify_admin_session)):
    return {"results": store.list_results(), "decisions": store.list_decisions()}


class DecisionBody(BaseModel):
    verdict: str = Field(..., pattern=r"^(approved_for_training|needs_more_data|rejected)$")
    note: str | None = Field(None, max_length=500)


@router.post("/admin/mos/decision", dependencies=[Depends(verify_csrf_origin)])
async def admin_record_decision(body: DecisionBody, admin: str = Depends(verify_admin_session)):
    """The admin's explicit sign-off on the current results — this is the
    ONLY thing that marks an eval round reviewed. Nothing here ever ships
    itself; recording a decision is a note for the humans running the next
    retrain, same as approving a pronunciation correction doesn't retrain
    the model by itself."""
    decision_id = store.record_decision(verdict=body.verdict, note=body.note, admin=admin)
    admin_audit_store.log(admin, body.verdict, "mos", decision_id, detail=body.note)
    return {"ok": True, "id": decision_id}


@router.get("/admin/mos/export")
async def admin_export(_admin: str = Depends(verify_admin_session)):
    rows = store.export_ratings()
    if not rows:
        raise HTTPException(status_code=404, detail="No ratings to export yet")
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=murya_mos_ratings.csv"},
    )
