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

import orjson
import sentry_sdk

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from rate_limit import ip_limiter, limiter
from orthography import normalize_digits, normalize_hausa_orthography

router = APIRouter()

_LANG = {"ha": "Hausa", "en": "English"}


def _dumps(obj) -> str:
    """Same _dumps helper as routers/chat.py -- orjson.dumps() returns
    bytes, decode() once here. Faster than stdlib json.dumps() on this
    endpoint's per-token streaming path, real UTF-8 for Hausa text instead
    of \\uXXXX-escaping."""
    return orjson.dumps(obj).decode()


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
@ip_limiter.limit("50/minute")
async def document_endpoint(request: Request, req: DocumentRequest):
    # Reuse the exact same tested provider functions the chat router uses --
    # including its per-provider cooldown tracker (_provider_available/
    # _note_provider_failure), shared as module-level state so a Groq/
    # Cerebras rate-limit hit via /api/chat also gets skipped here, and
    # vice versa, instead of each endpoint re-discovering the same outage.
    from routers.chat import (
        _note_provider_failure,
        _provider_available,
        stream_cerebras,
        stream_gemini_raw,
        stream_groq,
        stream_ollama,
    )

    from services.own_llm_service import (
        PROVIDER_NAME as OWN_LLM_NAME,
        own_llm_enabled,
        stream_own_llm,
    )

    messages = [
        {"role": "system", "content": _system_prompt(req.action, req.target)},
        {"role": "user", "content": req.text},
    ]

    async def generate():
        yield ": keepalive\n\n"
        full = ""

        async def try_provider(stream_fn):
            nonlocal full, produced_any
            async for delta in stream_fn:
                if delta:
                    produced_any = True
                full += delta
                yield f"data: {_dumps({'text': normalize_digits(full), 'isDone': False})}\n\n"

        for stream_fn, label in (
            *(((stream_own_llm(messages), OWN_LLM_NAME),) if own_llm_enabled() else ()),
            (stream_cerebras(messages), "Cerebras"),
            (stream_groq(messages), "Groq"),
            (stream_ollama(messages), "Ollama"),
            (stream_gemini_raw(messages), "Gemini"),
        ):
            if not _provider_available(label):
                print(f"[Murya] document {req.action}: {label} still in cooldown from a recent "
                      "rate-limit/quota error; skipping straight to the next provider.")
                continue
            full = ""
            produced_any = False
            try:
                async for event in try_provider(stream_fn):
                    yield event
            except Exception as exc:
                _note_provider_failure(label, exc)
                print(f"[Murya] document {req.action}: {label} failed ({type(exc).__name__}: {exc}), trying next provider...")
                full = ""
                continue
            if produced_any:
                break
            # A stream that completes with zero chunks and no exception (a
            # provider effectively returning nothing) used to look exactly
            # like a successful, complete translation/summary -- the
            # request finished with isDone:true and an empty body instead
            # of continuing to the next provider. Treat empty-but-clean the
            # same as a failure.
            print(f"[Murya] document {req.action}: {label} produced no content, trying next provider...")
            full = ""
        else:
            # All three providers failed. Same reasoning as chat.py's
            # matching capture_message -- see that comment for the finding
            # that motivated it. No-op when SENTRY_DSN isn't set.
            sentry_sdk.capture_message(
                f"All document {req.action} providers failed/empty for one request",
                level="warning",
            )
            yield f"data: {_dumps({'text': '', 'isDone': True, 'error': 'An kasa aiwatarwa a yanzu. A sake gwadawa. (Could not complete right now.)'})}\n\n"
            return

        out = normalize_digits(full)
        if req.target == "ha":
            out = normalize_hausa_orthography(out)
        yield f"data: {_dumps({'text': out, 'isDone': True})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
