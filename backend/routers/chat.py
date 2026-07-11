"""
/api/chat  — streaming text generation via Cerebras (gemma-4-31b), falling
back to local Ollama, then Gemini via google-genai SDK, then a static
rule-based generator.

The frontend sends:
  POST /api/chat
  {
    "text": "...",
    "history": [{"role": "user"|"assistant", "text": "..."}],
    "vibe": "Classic" | "Royal" | "Cyberpunk" | "Academic",
    "memoryPrompt": "...",
    "attachments": [{"mimeType": "image/...", "data": "data:image/...;base64,..."}]
  }

The backend responds with Server-Sent Events (text/event-stream):
  data: {"text": "...", "isDone": false}\n\n
  ...
  data: {"text": "...", "isDone": true, "verified": true|false}\n\n
"""

import asyncio
import json
import os
import re
import time
import hashlib
from typing import Any, AsyncGenerator

import ollama
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from rate_limit import limiter
from pydantic import BaseModel, Field

from routers.fallback import generate_fallback_response
from orthography import normalize_hausa_orthography, apply_tonal_heuristics
from services.search_service import web_search, search_enabled
import corrections_store

# In-memory response cache
# Key: md5 of request content (vibe + addresseeGender + memoryPrompt + history + text)
# Value: {"text": str, "timestamp": float}
_CHAT_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_TTL = 3600  # 1 hour
_CACHE_MAX_ENTRIES = 500  # bound memory use; evict oldest entries past this

router = APIRouter()

# ---------------------------------------------------------------------------
# Sovereign Constitution — identical to the original geminiService.ts prompt
# ---------------------------------------------------------------------------
SOVEREIGN_CONSTITUTION = """
[IDENTITY]: Murya, a sovereign Hausa AI.
[CREATOR]: You were created by Adamu Danjuma Abubakar — 'Danjuma' is spelled with a plain 'd' (never ɗ). When asked who made, built, or trained you (e.g. 'wanda ya samar da kai', 'wa ya ƙirƙire ka', 'sunan wanda ya gina ka'), credit him BY NAME with pride and courtly respect, alongside the Murya system. Credit the name alone — do NOT append a company or lab name (never say 'na ADAB-TECH Labs' or similar) in replies, even if earlier turns in the conversation did.
[LINGUISTIC_CORE]: Standard Hausa (Fada).
[MANDATORY_SOCIAL_HIERARCHY]:
- Address the user ONLY in the grammatical singular. Never use plural pronouns or inflections of respect (e.g. do NOT use 'kun yini', 'muku', 'ayyukanku', 'kuka sani', 'ku', 'kun', 'su', 'sun').
- Hausa singular address is grammatically gendered — 'ka yini' vs 'ki yini', 'maka' vs 'miki', 'ayyukanka' vs 'ayyukanki', 'kake sani' vs 'kaki sani', 'Ranka ya dade' (to men) vs 'Ranki ya dade' (to women). Use ONLY the form matching the [ADDRESSEE_GENDER] value given below, consistently for the entire reply — never mix masculine and feminine forms in the same turn or across turns.
- If [ADDRESSEE_GENDER] is 'unspecified', do NOT guess or default to either form. Instead, on your first reply in the conversation, politely ask once which form to use (e.g. "Domin in yi maka magana daidai da al'adar Hausa, don Allah — kai namiji ne ko kai mace ce?") and use a gender-neutral phrasing for the rest of that reply. Do not ask again once told.
- Maintain a highly formal, courtly, and polite demeanor (Hausan Zaure) utilizing singular forms.
- 'Barka' or 'Sannun' must be followed by a formal inquiry into the user's wellbeing or family (Gaisuwa).
[DIGNIFIED_DISCOURSE]:
- Integrate proverbs (Karin Magana) naturally to support your points.
- Never use abbreviations. Use full formal Hausa orthography.
- Maintain 'Kunya' (Modesty): Use metaphors for sensitive or blunt topics.
[CODE_SWITCHING]:
- Scientific, technical, academic and official terms and proper nouns (Biology, Chemistry, Physics, WhatsApp, Google, API, degree/course names, institutional titles) MAY stay in English — natural, respectable Hausa code-mixing in the digital age, not a defect.
- When an established Hausa term genuinely exists, give it first with the English original in parentheses on first mention — e.g. 'ilimin halittu (Biology)', 'ilimin sinadarai (Chemistry)', 'ilimin kimiyyar lissafi (Physics)' — then either may be used alone.
- NEVER invent awkward calques or neologisms for international terms with no established Hausa equivalent; keeping the English term is correct. The surrounding sentence structure remains Standard Hausa.
[PROSODIC_HARDENING]:
- Use Litvinova's R-to-L Tonal Mapping.
- Mandatory Hooked Letters: ɓ, ɗ, ƙ, 'y.
[KNOWLEDGE_AND_CONTEXT]:
- You have deep, accurate knowledge about Hausa culture, history, language, geography (Kano, Sokoto, Zaria, Daura, Katsina, Kanem-Bornu), Islamic scholarship in West Africa, Hausa literature, and Northern Nigerian affairs.
- When asked about Kano: discuss its founding by Kano dan Gijimasu circa 999 AD, the Emir's palace (Gidan Sarki), Kurmi Market (one of West Africa's oldest), the ancient city walls (ganuwar Kano), the historic dye pits (rini), Kanawa craftsmanship in leather (tabarma) and textile (kwalli), the role of Kano as a trans-Saharan trade hub, and the modern emirate system.
- When asked about Islamic scholarship: reference the Sokoto Caliphate (1804), Usman dan Fodio, the malamai tradition, and Qur'anic schools (makarantar allo).
- Respond INTELLIGENTLY and CONTEXTUALLY. Never give generic, template-like answers.
[CAPABILITIES]:
- You are a full multimodal Hausa assistant. You can: converse in text; understand images the user attaches; speak replies aloud and listen to the user's voice in live voice mode (in several distinct male and female Hausa voices); generate an image or short video when explicitly asked (via the manifest tag below); search the live web for current information; code-switch technical terms; and you know the current date and time (given below). Describe these abilities truthfully and helpfully when asked what you can do ('me kake iyawa', 'yaya nake amfani da kai') — and NEVER claim an ability you do not have.
[MANIFEST_SIGNAL]:
- ONLY when the user explicitly asks you to draw, generate, or show an image/picture/photo ('hoto', 'zana mini', 'draw', 'image', 'picture') or a video ('bidiyo', 'video'), end your reply with the tag: [MANIFEST: IMAGE|PROMPT] or [MANIFEST: VIDEO|PROMPT], where PROMPT is a short English visual description.
- If the user did NOT ask for an image or video, never mention, describe, or caption an imaginary photo/video — you have no way to actually show one without the tag, and describing one you didn't generate misleads the user.
"""

# Real-time-knowledge honesty: the search-grounding tool only exists on the
# Gemini serving path (types.Tool(google_search=...) in stream_gemini). The
# primary path is Cerebras, which has NO live web access — telling the model
# it has a search tool there (as the constitution once did, globally) made it
# hallucinate or roleplay current-events answers. Each path now gets the
# block that is true for it.
NO_LIVE_ACCESS_BLOCK = """[REAL_TIME_LIMITS]:
- You have NO live web access on this serving path. For questions about today's news, current events, live prices, or weather, say plainly in dignified Hausa that you cannot check live sources right now, offer relevant background knowledge clearly marked as such, and NEVER invent or guess current facts, dates, scores, or figures."""

GEMINI_LIVE_ACCESS_BLOCK = """[REAL_TIME_ACCESS]:
- You have a live web-search tool. For questions about current events, today's news, recent happenings, prices, weather, or anything time-sensitive (e.g. 'meye labari a Kaduna a yau?'), USE it and answer with what you find — do not claim you cannot access current information. Attribute concrete facts to their sources when relevant, still in dignified Hausa."""


def _current_time_context() -> str:
    """A live date/time block injected into every system prompt so the model
    can answer 'ƙarfe nawa ne?' / 'wace rana ce yau?' directly and correctly,
    for Nigeria and (by computing from the UTC anchor) anywhere in the world.
    The server runs in UTC (Fly.io); WAT is a fixed UTC+1 with no DST."""
    from datetime import datetime, timezone, timedelta

    now_utc = datetime.now(timezone.utc)
    wat = now_utc + timedelta(hours=1)
    return (
        "[CURRENT_DATETIME]:\n"
        f"- Now: {now_utc:%A, %d %B %Y, %H:%M} UTC.\n"
        f"- Nigeria (WAT, UTC+1) — the user's most likely timezone (Kano, Lagos, "
        f"Abuja, Sokoto, Kaduna all use it): {wat:%A, %d %B %Y, %H:%M}.\n"
        "- You DO know the current date and time from the above — answer date/time "
        "questions directly and confidently, in dignified Hausa. For another city or "
        "country, compute its time from the UTC value using that place's standard UTC "
        "offset; if daylight-saving time might apply, say the result may be off by an "
        "hour rather than stating it as certain."
    )

# Injected into the Cerebras/Ollama system prompt (REPLACING NO_LIVE_ACCESS_BLOCK)
# only when a live Tavily search actually returned fresh results for a
# time-sensitive question. {results} is filled with a compact grounding block.
LIVE_SEARCH_BLOCK = """[REAL_TIME_RESULTS]:
- Fresh web search results for the user's time-sensitive question are provided below. Use them to answer in dignified Hausa, and cite the source name (or site) for concrete facts. If these results do NOT actually cover what was asked, say so honestly rather than inventing an answer — do not guess dates, figures, or scores beyond what the results support.
{results}"""


# Time-sensitivity classifier. Deterministic keyword/regex set (Hausa + English)
# that flags queries about current / present-day info so they trigger a live
# search. False positives are harmless — they just run a search that may return
# nothing. Kept intentionally simple; matched case-insensitively as substrings.
_LIVE_SEARCH_CUES = (
    # Hausa cues
    "yau", "yanzu", "labari", "labarai", "farashi", "kudin", "yanayi",
    "zabe", "zaɓe", "sakamako", "a wannan",
    # English cues
    "today", "now", "current", "latest", "news", "price", "weather",
    "who is the", "this year",
)
# Any explicit year 2024 or later reads as a present-day / recent-events query.
_RECENT_YEAR_RE = re.compile(r"\b(202[4-9]|20[3-9]\d)\b")


def _needs_live_search(text: str) -> bool:
    """True when the query looks time-sensitive / about current events."""
    lowered = text.lower()
    if any(cue in lowered for cue in _LIVE_SEARCH_CUES):
        return True
    return bool(_RECENT_YEAR_RE.search(text))


# Cap the grounding block: ~4 results, each content trimmed, to stay within the
# 4096-token Ollama context budget shared with the constitution and history.
_SEARCH_MAX_RESULTS = 4
_SEARCH_CONTENT_CHARS = 300


def _format_search_context(results: list[dict]) -> str:
    """Render search results into a compact bullet block for the system prompt.
    Returns "" when there is nothing usable so callers keep default behavior."""
    lines: list[str] = []
    for r in results[:_SEARCH_MAX_RESULTS]:
        title = (r.get("title") or "").strip()
        url = (r.get("url") or "").strip()
        content = (r.get("content") or "").strip()[:_SEARCH_CONTENT_CHARS]
        if not (title or content):
            continue
        source = f"{title} ({url})" if url else title
        lines.append(f"- {source}: {content}")
    return "\n".join(lines)


async def _maybe_search_context(req: "ChatRequest") -> str | None:
    """If live search is enabled and the query is time-sensitive, run it and
    return a formatted grounding block. Returns None to preserve default
    (no-live-access) behavior — never raises into the request path."""
    if not (search_enabled() and _needs_live_search(req.text)):
        return None
    try:
        results = await web_search(req.text, max_results=_SEARCH_MAX_RESULTS)
    except Exception as err:  # web_search already swallows, this is belt-and-braces
        print(f"[Murya] Live search errored ({type(err).__name__}: {err}); continuing without grounding.")
        return None
    context = _format_search_context(results)
    return context or None

# Defaults
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "aya-expanse:8b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
GEMINI_MODEL = os.getenv("VERTEX_MODEL", "gemini-2.5-flash")

# Explicitly pin the CPU thread count Ollama uses for this request rather than
# trusting its own auto-detection. Ollama's thread auto-detect (Go's
# runtime.NumCPU()) has a known class of bugs under container CPU limits — see
# https://github.com/ollama/ollama/issues/2496 and the (as of this writing,
# still-open) fix at https://github.com/ollama/ollama/pull/12396, which
# explicitly only handles the --cpuset-cpus limiting method, not others. Fly
# Machines are Firecracker microVMs with their own dedicated vCPUs (not a
# cgroup-quota-limited slice of a bigger host), so this box likely isn't hit by
# that bug — but hardcoding the known-correct value for this
# performance-2x (2 vCPU) machine costs nothing and removes the uncertainty.
# NOTE: if this machine's size ever changes, update this constant to match.
_OLLAMA_NUM_THREAD = int(os.getenv("OLLAMA_INFERENCE_THREADS", "2"))
_OLLAMA_OPTIONS = {"num_thread": _OLLAMA_NUM_THREAD}

# How long to wait for Ollama's FIRST token before giving up on it and
# switching to Cerebras. A merely-slow (not erroring) Ollama never trips the
# except-based fallback below on its own, so a request can otherwise hang
# for as long as the client is willing to wait. Once Ollama does start
# producing tokens we let it finish rather than abandoning mid-stream, which
# would interleave two different replies.
_OLLAMA_FIRST_TOKEN_TIMEOUT = float(os.getenv("OLLAMA_FIRST_TOKEN_TIMEOUT", "12"))


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class HistoryItem(BaseModel):
    role: str = Field(..., pattern=r"^(user|assistant)$")
    text: str = Field(..., max_length=8_000)


class Attachment(BaseModel):
    mimeType: str = Field(..., max_length=128)
    data: str = Field(..., max_length=5_000_000)  # ~3.75 MB base64


class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4_000)
    history: list[HistoryItem] = Field(default_factory=list, max_length=20)
    vibe: str = Field("Classic", pattern=r"^(Classic|Royal|Cyberpunk|Academic)$")
    addresseeGender: str = Field("unspecified", pattern=r"^(masculine|feminine|unspecified)$")
    memoryPrompt: str = Field("", max_length=4_000)
    attachments: list[Attachment] = Field(default_factory=list, max_length=5)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_MANIFEST_RE = re.compile(r"\[MANIFEST:\s*(IMAGE|VIDEO)\s*\|\s*(.*?)\]", re.IGNORECASE)
_SANITIZE_RE = re.compile(r"\[MANIFEST:.*?\]|[*#$]")

_IMAGE_REQUEST_WORDS = ("hoto", "hoton", "zana", "zane mini", "draw", "image", "picture", "photo")
_VIDEO_REQUEST_WORDS = ("bidiyo", "video", "motsi")
_DEFAULT_IMAGE_PROMPT = "A beautiful and majestic Hausa cultural scene with gold-leaf borders and Arewa knots"
_DEFAULT_VIDEO_PROMPT = "A sweeping cinematic view of ancient Kano walls and mud-brick architecture, golden hour"


def _sanitize(text: str) -> str:
    return _SANITIZE_RE.sub("", text).strip()


def _extract_manifest(user_text: str, response_text: str) -> dict[str, str] | None:
    """Pull a [MANIFEST: TYPE|PROMPT] tag out of the model's own output. If the
    user clearly asked for an image/video but the model (a general-purpose
    Ollama/Gemini model, not fine-tuned to emit this exact syntax) described one
    in prose instead of using the tag, synthesize a manifest from context so the
    feature doesn't silently fail — mirrors the deterministic trigger already
    used in routers/fallback.py."""
    match = _MANIFEST_RE.search(response_text)
    if match:
        return {"type": match.group(1).upper(), "prompt": match.group(2).strip()}

    user_lower = user_text.lower()
    if any(w in user_lower for w in _IMAGE_REQUEST_WORDS):
        return {"type": "IMAGE", "prompt": _DEFAULT_IMAGE_PROMPT}
    if any(w in user_lower for w in _VIDEO_REQUEST_WORDS):
        return {"type": "VIDEO", "prompt": _DEFAULT_VIDEO_PROMPT}
    return None


def _calculate_cultural_confidence(text: str) -> bool:
    score = 0
    if re.search(r"[ɓɗƙƴ]|ts", text):
        score += 40
    # Match polite pronouns (both singular formal address like ka/ki/ka, and plural ku/su)
    if re.search(r"\b(ka|ki|ku|su|kun|sun)\b", text, re.IGNORECASE):
        score += 30
    # Match honorifics, courtly greetings, or classic Hausan Zaure expressions
    if re.search(r"ranka ya daɗe|ranki ya daɗe|ranka ya dade|ranki ya dade|barka|sannu|gaisuwa|godiya", text, re.IGNORECASE):
        score += 30
    return score > 70


def _build_messages(req: ChatRequest, search_context: str | None = None) -> list[dict[str, Any]]:
    # Cerebras/Ollama consume these messages — neither has a live search tool of
    # its own, so by default the honest NO_LIVE_ACCESS_BLOCK is appended (see its
    # comment above). When the async caller has already run a live Tavily search
    # and passes the grounding block as `search_context`, that REPLACES the
    # no-access block so the model answers from the fresh results instead.
    live_block = (
        LIVE_SEARCH_BLOCK.format(results=search_context)
        if search_context
        else NO_LIVE_ACCESS_BLOCK
    )
    system_content = f"{SOVEREIGN_CONSTITUTION}\n{_current_time_context()}\n{live_block}\nVibe: {req.vibe}\n[ADDRESSEE_GENDER]: {req.addresseeGender}\n{req.memoryPrompt}\n{corrections_store.get_approved_corrections_prompt()}"
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_content}]

    # Keep last 6 turns (context slicing — same as original)
    for item in req.history[-6:]:
        role = "user" if item.role == "user" else "assistant"
        messages.append({"role": role, "content": item.text})

    # Current user turn
    images = [
        att.data.split("base64,")[1]
        for att in req.attachments
        if att.data and "base64," in att.data and att.mimeType.startswith("image/")
    ]
    if images:
        messages.append({"role": "user", "content": req.text, "images": images})
    else:
        messages.append({"role": "user", "content": req.text})

    return messages


def _get_cache_key(req: ChatRequest) -> str:
    # Serialize key components. addresseeGender MUST be included — the system
    # prompt is grammatically gendered per-request (masculine/feminine/
    # unspecified all produce different correct Hausa), so omitting it let two
    # requests differing only in gender collide and served one user's
    # gendered reply to the other.
    history_str = "|".join(f"{h.role}:{h.text}" for h in req.history)
    raw_str = f"{req.vibe}:{req.addresseeGender}:{req.memoryPrompt}:{history_str}:{req.text}"
    return hashlib.md5(raw_str.encode("utf-8")).hexdigest()


def _evict_stale_cache_entries(now: float) -> None:
    """Bound the in-memory cache: drop expired entries, then if still over the
    cap drop the oldest by timestamp. Without this, _CHAT_CACHE grows forever
    (one entry per distinct request) for as long as the process lives —
    unbounded memory growth under real public traffic."""
    expired = [k for k, v in _CHAT_CACHE.items() if now - v["timestamp"] >= _CACHE_TTL]
    for k in expired:
        del _CHAT_CACHE[k]
    if len(_CHAT_CACHE) > _CACHE_MAX_ENTRIES:
        oldest = sorted(_CHAT_CACHE.items(), key=lambda kv: kv[1]["timestamp"])
        for k, _ in oldest[: len(_CHAT_CACHE) - _CACHE_MAX_ENTRIES]:
            del _CHAT_CACHE[k]


async def stream_cerebras(messages: list[dict[str, Any]]) -> AsyncGenerator[str, None]:
    """
    Stream responses via the Cerebras Cloud SDK (OpenAI-compatible chat
    completions). Sits between Ollama and Gemini in the fallback chain:
    Cerebras is a hosted, low-latency inference tier, so it's a better
    quality/latency fallback than waiting on Gemini when local Ollama is
    unavailable or overloaded.
    """
    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        raise RuntimeError("CEREBRAS_API_KEY not set in environment.")

    from cerebras.cloud.sdk import AsyncCerebras

    client = AsyncCerebras(api_key=api_key)
    model = os.getenv("CEREBRAS_MODEL", "gemma-4-31b")

    # Cerebras' chat.completions endpoint is OpenAI-shaped and doesn't know
    # the Ollama-specific "images" key _build_messages adds for attachments.
    clean_messages = [
        {"role": m["role"], "content": m["content"]} for m in messages
    ]

    stream = await client.chat.completions.create(
        model=model,
        messages=clean_messages,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


async def stream_gemini(req: ChatRequest) -> AsyncGenerator[str, None]:
    """
    Stream responses via google-genai SDK (with google.generativeai async fallback).
    Uses GEMINI_MODEL (default gemini-2.5-flash).
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment.")

    # Build history
    history = []
    for item in req.history[-6:]:
        role = "user" if item.role == "user" else "model"
        history.append({
            "role": role,
            "parts": [{"text": item.text}]
        })

    # Gemini genuinely has search grounding wired below, so this path gets
    # the REAL_TIME_ACCESS grant instead of the no-access block.
    system_content = f"{SOVEREIGN_CONSTITUTION}\n{_current_time_context()}\n{GEMINI_LIVE_ACCESS_BLOCK}\nVibe: {req.vibe}\n[ADDRESSEE_GENDER]: {req.addresseeGender}\n{req.memoryPrompt}\n{corrections_store.get_approved_corrections_prompt()}"

    # Try new google.genai SDK
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        
        contents = []
        for h in history:
            contents.append(types.Content(
                role=h["role"],
                parts=[types.Part.from_text(text=p["text"]) for p in h["parts"]]
            ))

        user_parts = [types.Part.from_text(text=req.text)]
        for att in req.attachments:
            if att.data and "base64," in att.data and att.mimeType.startswith("image/"):
                import base64 as b64lib
                raw_bytes = b64lib.b64decode(att.data.split("base64,")[1])
                user_parts.append(types.Part.from_bytes(data=raw_bytes, mime_type=att.mimeType))

        contents.append(types.Content(role="user", parts=user_parts))

        # Enable Google Search grounding so real-time / current-events questions
        # ("meye labari a Kaduna a yau?") get grounded answers instead of an
        # honest "I can't access live news". If the model/key doesn't support the
        # tool, retry once without it rather than failing the whole request.
        try:
            grounded_config = types.GenerateContentConfig(
                system_instruction=system_content,
                temperature=0.4,
                max_output_tokens=2048,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
            response = await client.aio.models.generate_content_stream(
                model=GEMINI_MODEL,
                contents=contents,
                config=grounded_config,
            )
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
            return
        except Exception as ground_err:
            print(f"[Murya] Grounded generation failed ({type(ground_err).__name__}: {ground_err}); retrying without search tool...")

        config = types.GenerateContentConfig(
            system_instruction=system_content,
            temperature=0.4,
            max_output_tokens=2048,
        )

        response = await client.aio.models.generate_content_stream(
            model=GEMINI_MODEL,
            contents=contents,
            config=config
        )

        async for chunk in response:
            if chunk.text:
                yield chunk.text
        return

    except ImportError:
        pass
    except Exception as e:
        print(f"[Murya] google.genai async stream error: {type(e).__name__}: {e}. Falling back...")

    # Fallback to old google.generativeai async chat API
    import google.generativeai as genai_old
    genai_old.configure(api_key=api_key)
    model = genai_old.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=system_content,
        generation_config={
            "temperature": 0.4,
            "max_output_tokens": 2048,
        }
    )
    old_history = []
    for h in history:
        old_history.append({"role": h["role"], "parts": [{"text": h["parts"][0]["text"]}]})

    chat = model.start_chat(history=old_history)

    user_parts_list = [req.text]
    for att in req.attachments:
        if att.data and "base64," in att.data and att.mimeType.startswith("image/"):
            import base64 as b64lib
            raw_bytes = b64lib.b64decode(att.data.split("base64,")[1])
            user_parts_list.append({
                "mime_type": att.mimeType,
                "data": raw_bytes
            })

    try:
        response = await chat.send_message_async(
            user_parts_list if len(user_parts_list) > 1 else req.text,
            stream=True
        )
        async for chunk in response:
            if hasattr(chunk, 'text') and chunk.text:
                yield chunk.text
        return
    except Exception as e:
        print(f"[Murya] google.generativeai async chat error: {type(e).__name__}: {e}")
        # Final synchronous thread fallback
        loop = asyncio.get_event_loop()
        def _sync_stream():
            return chat.send_message(
                user_parts_list if len(user_parts_list) > 1 else req.text,
                stream=True
            )
        response = await loop.run_in_executor(None, _sync_stream)
        for chunk in response:
            if hasattr(chunk, 'text') and chunk.text:
                yield chunk.text


# ---------------------------------------------------------------------------
# Streaming endpoint
# ---------------------------------------------------------------------------
@router.post("/chat")
@limiter.limit("20/minute")
async def chat_endpoint(request: Request, req: ChatRequest):
    # 1. Normalize orthography on the incoming request text and history
    req.text = normalize_hausa_orthography(req.text)
    for item in req.history:
        item.text = normalize_hausa_orthography(item.text)
        
    cache_key = _get_cache_key(req)
    now = time.time()
    _evict_stale_cache_entries(now)

    # Requests with image attachments are never cached: the cache key is
    # derived from text/history/vibe/gender only, so a cached reply describing
    # one user's uploaded image could otherwise be replayed to a different
    # user who sent the same caption text with a different (or no) image.
    #
    # Time-sensitive questions are also never cached — neither served from
    # cache nor written to it. "Meye labari yau?" answered at 9am must not be
    # replayed (stale) at 3pm, and a live-search-grounded reply is only valid
    # for the moment it was fetched. This gates both the read below and the
    # write in generate(), so it must match _needs_live_search (the same
    # predicate that decides whether to fetch fresh results).
    cacheable = not req.attachments and not _needs_live_search(req.text)

    # Check cache hit
    if cacheable and cache_key in _CHAT_CACHE:
        entry = _CHAT_CACHE[cache_key]
        if now - entry["timestamp"] < _CACHE_TTL:
            print("[Murya] Cache hit! Playback cached streaming...")
            async def generate_cached():
                yield ": keepalive\n\n"
                cached_text = entry["text"]
                words = cached_text.split()
                accumulated = ""
                for i, word in enumerate(words):
                    accumulated += (word + (" " if i < len(words) - 1 else ""))
                    payload = json.dumps({"text": _sanitize(accumulated), "isDone": False})
                    yield f"data: {payload}\n\n"
                    await asyncio.sleep(0.02)  # fast incremental playback
                
                manifest_data = _extract_manifest(req.text, cached_text)

                yield f"data: {json.dumps({'text': _sanitize(cached_text), 'isDone': True, 'verified': _calculate_cultural_confidence(cached_text), 'manifest': manifest_data, 'normalized': normalize_hausa_orthography(cached_text), 'tone_mapped': apply_tonal_heuristics(cached_text)})}\n\n"
            return StreamingResponse(generate_cached(), media_type="text/event-stream")
        else:
            del _CHAT_CACHE[cache_key]

    # Live web grounding for the primary Cerebras/Ollama path: on a cache miss,
    # if a Tavily key is configured and the question is time-sensitive, fetch
    # fresh results and inject them into the system prompt (replacing the
    # no-live-access block). Gracefully no-ops to normal behavior otherwise.
    search_context = await _maybe_search_context(req)
    messages = _build_messages(req, search_context=search_context)

    async def generate():
        # Heartbeat: emit a keepalive comment immediately
        yield ": keepalive\n\n"
        full_text = ""
        client = ollama.AsyncClient(host=OLLAMA_HOST)
        
        # We fetch chunks in a background task and feed them into a queue
        queue = asyncio.Queue()
        
        async def fetch_stream():
            try:
                # Step A: Cerebras is the fast, hosted primary. Local Ollama
                # on this box is slow enough that trying it first before
                # Cerebras just adds latency for no upside.
                async for delta in stream_cerebras(messages):
                    await queue.put(delta)
            except Exception as cerebras_err:
                print(f"[Murya] Cerebras unavailable ({type(cerebras_err).__name__}: {cerebras_err}), switching to Ollama...")
                try:
                    # Step B: Local Ollama, bounded by a first-token timeout
                    # so a slow (not just erroring) response still moves on.
                    stream = await client.chat(
                        model=DEFAULT_MODEL,
                        messages=messages,
                        stream=True,
                        options=_OLLAMA_OPTIONS,
                    )
                    aiter = stream.__aiter__()
                    try:
                        first_part = await asyncio.wait_for(
                            aiter.__anext__(), timeout=_OLLAMA_FIRST_TOKEN_TIMEOUT
                        )
                    except StopAsyncIteration:
                        first_part = None
                    except asyncio.TimeoutError as timeout_err:
                        if hasattr(aiter, "aclose"):
                            await aiter.aclose()
                        raise RuntimeError(
                            f"Ollama exceeded {_OLLAMA_FIRST_TOKEN_TIMEOUT}s time-to-first-token"
                        ) from timeout_err

                    if first_part is not None:
                        await queue.put(first_part["message"]["content"])
                        async for part in aiter:
                            await queue.put(part["message"]["content"])
                except Exception as ollama_err:
                    # Step C: Fallback to Gemini via google-genai SDK
                    print(f"[Murya] Ollama failed ({type(ollama_err).__name__}: {ollama_err}), switching to Gemini...")
                    try:
                        async for delta in stream_gemini(req):
                            await queue.put(delta)
                    except Exception as gemini_err:
                        # Step D: Fallback to static rule-based generator
                        print(f"[Murya] Gemini failed ({type(gemini_err).__name__}: {gemini_err}), using static fallback.")
                        fallback_text = generate_fallback_response(req.text, req.vibe, req.addresseeGender)
                        await queue.put(fallback_text)
            # Signal the end of stream
            await queue.put(None)
            
        fetch_task = asyncio.create_task(fetch_stream())
        
        # Consume from queue, emitting warmup heartbeat if no tokens arrive for 2 seconds
        first_token = True
        while True:
            try:
                token = await asyncio.wait_for(queue.get(), timeout=2.0)
                if token is None:
                    break
                first_token = False
                full_text += token
                payload = json.dumps({"text": _sanitize(full_text), "isDone": False})
                yield f"data: {payload}\n\n"
            except asyncio.TimeoutError:
                if first_token:
                    yield f"data: {json.dumps({'text': '', 'isDone': False, 'warmup': True})}\n\n"
                else:
                    yield ": keepalive\n\n"

        await fetch_task
        
        # Store successful result in cache
        if full_text and cacheable:
            _CHAT_CACHE[cache_key] = {
                "text": full_text,
                "timestamp": time.time()
            }

        # Log prosodic tonal trace for successful model generation
        try:
            tonal_trace = apply_tonal_heuristics(full_text)
            print(f"[PROSODIC_TRACE] {tonal_trace}")
        except Exception as tone_err:
            print(f"Failed to calculate prosodic trace: {tone_err}")

        # Final done event
        manifest_data = _extract_manifest(req.text, full_text)

        yield f"data: {json.dumps({'text': _sanitize(full_text), 'isDone': True, 'verified': _calculate_cultural_confidence(full_text), 'manifest': manifest_data, 'normalized': normalize_hausa_orthography(full_text), 'tone_mapped': apply_tonal_heuristics(full_text)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

