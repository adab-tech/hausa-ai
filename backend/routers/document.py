"""
/api/document — one-shot translate / summarize for pasted text.

Separate from /api/chat because these are single-turn document tasks, not a
conversation: no history, no persona, a task-specific system prompt, and a much
larger input cap (Cerebras' 131k context easily handles long documents).

Same Cerebras -> Ollama -> Gemini fallback chain as /api/chat (reusing the
exact same tested functions from routers.chat), MINUS the chat persona/search
grounding/static-proverb fallback — none of that belongs in a translate/
summarize task. Added 2026-08-22 after this endpoint was found calling
Cerebras only, with zero fallback: once Cerebras started returning 402
(payment required), every single request here failed outright.

POST /api/document
  { "text": "...", "action": "translate"|"summarize", "target": "ha"|"en" }
  -> Server-Sent Events: {"text": "...", "isDone": false} ... {"text": "...", "isDone": true}
"""

import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from rate_limit import limiter
from orthography import normalize_digits, normalize_hausa_orthography

router = APIRouter()

_LANG = {"ha": "Hausa", "en": "English"}


class DocumentRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=30_000)
    action: str = Field(..., pattern=r"^(translate|summarize)$")
    target: str = Field("ha", pattern=r"^(ha|en)$")


def _system_prompt(action: str, target: str) -> str:
    lang = _LANG[target]
    hausa_note = (
        "Use correct Standard Hausa orthography with the hooked letters "
        "ɓ, ɗ, ƙ, ƴ where they belong. "
        if target == "ha"
        else ""
    )
    if action == "translate":
        return (
            f"You are a faithful, fluent translator. Translate the user's text into {lang}. "
            f"Preserve meaning, tone, proper names, numbers, and paragraph structure. {hausa_note}"
            "Output ONLY the translation — no preamble, no notes, no explanation."
        )
    return (
        f"You are a careful summarizer. Summarize the user's text in {lang}, capturing the key "
        f"points faithfully and concisely (short paragraphs or bullet points, whichever fits). "
        f"{hausa_note}Output ONLY the summary — no preamble."
    )


@router.post("/document")
@limiter.limit("10/minute")
async def document_endpoint(request: Request, req: DocumentRequest):
    # Reuse the exact same tested provider functions the chat router uses.
    from routers.chat import stream_cerebras, stream_gemini_raw, stream_ollama

    messages = [
        {"role": "system", "content": _system_prompt(req.action, req.target)},
        {"role": "user", "content": req.text},
    ]

    async def generate():
        yield ": keepalive\n\n"
        full = ""

        async def try_provider(stream_fn):
            nonlocal full
            async for delta in stream_fn:
                full += delta
                yield f"data: {json.dumps({'text': normalize_digits(full), 'isDone': False})}\n\n"

        for stream_fn, label in (
            (stream_cerebras(messages), "Cerebras"),
            (stream_ollama(messages), "Ollama"),
            (stream_gemini_raw(messages), "Gemini"),
        ):
            full = ""
            try:
                async for event in try_provider(stream_fn):
                    yield event
                break
            except Exception as exc:
                print(f"[Murya] document {req.action}: {label} failed ({type(exc).__name__}: {exc}), trying next provider...")
                full = ""
                continue
        else:
            # All three providers failed.
            yield f"data: {json.dumps({'text': '', 'isDone': True, 'error': 'An kasa aiwatarwa a yanzu. A sake gwadawa. (Could not complete right now.)'})}\n\n"
            return

        out = normalize_digits(full)
        if req.target == "ha":
            out = normalize_hausa_orthography(out)
        yield f"data: {json.dumps({'text': out, 'isDone': True})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
