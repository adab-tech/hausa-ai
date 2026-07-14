"""
Pronunciation corrections — the human-in-the-loop TTS eval loop.

PUBLIC (user):
  POST /api/pronunciation/flag        — "this was mispronounced" (text, no audio)

ADMIN (reviewer, self-gated via verify_admin_session):
  GET    /api/admin/pronunciation             — list items (optional ?status=)
  GET    /api/admin/pronunciation/counts      — pending/approved/rejected tallies
  POST   /api/admin/pronunciation             — record a NEW correction (text + audio)
  POST   /api/admin/pronunciation/{id}/record — record audio against an existing flag
  GET    /api/admin/pronunciation/{id}/audio  — play a correction's recording (WAV)
  POST   /api/admin/pronunciation/{id}/status — approve / reject
  DELETE /api/admin/pronunciation/{id}        — remove

Approved recordings are used at synthesis time (see audio.py, highest priority)
and exported for the next voice retrain (utils/export_pronunciation_corpus.py).
"""

from fastapi import (APIRouter, Depends, File, Form, HTTPException, Request,
                     Response, UploadFile)
from pydantic import BaseModel, Field

import pronunciation_store as store
from auth import verify_admin_session
from contributor import get_contributor_id
from rate_limit import limiter

router = APIRouter()

_MAX_UPLOAD = 6 * 1024 * 1024  # 6 MB raw upload cap (converted PCM is smaller)


def _clean_speaker(speaker_id):
    """Accept 0..7 or None (voice-agnostic); reject anything else."""
    if speaker_id is None or speaker_id == "":
        return None
    try:
        s = int(speaker_id)
    except (TypeError, ValueError):
        return None
    return s if 0 <= s <= 7 else None


async def _read_audio(upload: UploadFile) -> bytes:
    """Read + size-check an uploaded recording, decode to 24 kHz PCM. Raises
    HTTPException on empty/oversized/undecodable input."""
    raw = await upload.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty audio upload")
    if len(raw) > _MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="Audio too large")
    pcm = store.convert_upload_to_pcm24k(raw)
    if not pcm:
        raise HTTPException(status_code=400, detail="Could not decode audio (try WAV/webm/mp3)")
    return pcm


# ---------------------------------------------------------------------------
# Public: flag a mispronunciation
# ---------------------------------------------------------------------------
class FlagBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=400)
    speaker_id: int | None = Field(None, ge=0, le=7)
    note: str | None = Field(None, max_length=500)


@router.post("/pronunciation/flag")
@limiter.limit("20/minute")
async def flag_mispronunciation(request: Request, body: FlagBody):
    """A user reports that a word/phrase was said wrong. Creates a pending item
    for a reviewer to record the correct pronunciation against."""
    row_id = store.flag(
        text=body.text,
        speaker_id=body.speaker_id,
        submitted_by=get_contributor_id(request),
        note=body.note,
    )
    if row_id is None:
        raise HTTPException(status_code=400, detail="Nothing to flag")
    return {"ok": True, "id": row_id}


@router.post("/pronunciation/submit")
@limiter.limit("6/minute")
async def submit_pronunciation(
    request: Request,
    text: str = Form(...),
    audio: UploadFile = File(...),
    speaker_id: str | None = Form(None),
    note: str | None = Form(None),
):
    """PUBLIC: a user records the correct pronunciation of a word/phrase (and may
    add a text note). Lands 'pending' — like every correction, it is NEVER served
    until the owner explicitly approves it in the admin panel. Rate-limited and
    size-capped; the audio must decode or it is rejected."""
    pcm = await _read_audio(audio)
    try:
        row_id = store.add_correction(
            text=text, speaker_id=_clean_speaker(speaker_id), audio_pcm=pcm,
            submitted_by=get_contributor_id(request), note=note, status="pending",
        )
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e))
    if row_id is None:
        raise HTTPException(status_code=400, detail="Missing text or audio")
    return {"ok": True, "id": row_id}


# ---------------------------------------------------------------------------
# Admin: review + record corrections
# ---------------------------------------------------------------------------
@router.get("/admin/pronunciation")
async def admin_list(status: str | None = None,
                     _admin: str = Depends(verify_admin_session)):
    return {"items": store.list_items(status=status), "counts": store.counts()}


@router.get("/admin/pronunciation/counts")
async def admin_counts(_admin: str = Depends(verify_admin_session)):
    return store.counts()


@router.post("/admin/pronunciation")
async def admin_create(
    request: Request,
    text: str = Form(...),
    audio: UploadFile = File(...),
    speaker_id: str | None = Form(None),
    note: str | None = Form(None),
    admin: str = Depends(verify_admin_session),
):
    """Reviewer records a NEW correction: the correct way to say `text`."""
    pcm = await _read_audio(audio)
    try:
        row_id = store.add_correction(
            text=text, speaker_id=_clean_speaker(speaker_id), audio_pcm=pcm,
            submitted_by=f"reviewer:{admin}", note=note, status="approved",
        )
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e))
    if row_id is None:
        raise HTTPException(status_code=400, detail="Missing text or audio")
    return {"ok": True, "id": row_id}


@router.post("/admin/pronunciation/{row_id}/record")
async def admin_record_against_flag(
    row_id: int,
    audio: UploadFile = File(...),
    _admin: str = Depends(verify_admin_session),
):
    """Reviewer records audio for an existing (flagged) item and approves it."""
    pcm = await _read_audio(audio)
    try:
        ok = store.attach_audio(row_id, pcm)
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True, "id": row_id}


@router.get("/admin/pronunciation/{row_id}/audio")
async def admin_get_audio(row_id: int, _admin: str = Depends(verify_admin_session)):
    """Serve a correction's recording as a WAV for playback in the dashboard."""
    from routers.audio import _add_wav_header
    pcm = store.get_audio(row_id)
    if not pcm:
        raise HTTPException(status_code=404, detail="No audio for this item")
    return Response(content=_add_wav_header(pcm, sample_rate=24000), media_type="audio/wav")


class StatusBody(BaseModel):
    status: str = Field(..., pattern=r"^(pending|approved|rejected)$")


@router.post("/admin/pronunciation/{row_id}/status")
async def admin_set_status(row_id: int, body: StatusBody,
                           _admin: str = Depends(verify_admin_session)):
    if not store.set_status(row_id, body.status):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True, "id": row_id, "status": body.status}


@router.delete("/admin/pronunciation/{row_id}")
async def admin_delete(row_id: int, _admin: str = Depends(verify_admin_session)):
    if not store.delete(row_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True, "id": row_id}
