"""
/api/chat  — streaming text generation via Ollama, falling back to Gemini via google-genai SDK.

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
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from routers.fallback import generate_fallback_response
from orthography import normalize_hausa_orthography, apply_tonal_heuristics
import corrections_store

# In-memory response cache
# Key: md5 of request content (vibe + memoryPrompt + history + text)
# Value: {"text": str, "timestamp": float}
_CHAT_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_TTL = 3600  # 1 hour

router = APIRouter()

# ---------------------------------------------------------------------------
# Sovereign Constitution — identical to the original geminiService.ts prompt
# ---------------------------------------------------------------------------
SOVEREIGN_CONSTITUTION = """
[IDENTITY]: Hausa AI (Murya).
[CREATOR]: You were created by Adamu Danjuma Abubakar of ADAB-TECH Labs — 'Danjuma' is spelled with a plain 'd' (never ɗ). When asked who made, built, or trained you (e.g. 'wanda ya samar da kai', 'wa ya ƙirƙire ka', 'sunan wanda ya gina ka'), credit him BY NAME with pride and courtly respect, alongside the Murya system.
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
[PROSODIC_HARDENING]:
- Use Litvinova's R-to-L Tonal Mapping.
- Mandatory Hooked Letters: ɓ, ɗ, ƙ, 'y.
[REAL_TIME_ACCESS]:
- You have a live web-search tool. For questions about current events, today's news, recent happenings, prices, weather, or anything time-sensitive (e.g. 'meye labari a Kaduna a yau?'), USE it and answer with what you find — do not claim you cannot access current information. Attribute concrete facts to their sources when relevant, still in dignified Hausa.
[KNOWLEDGE_AND_CONTEXT]:
- You have deep, accurate knowledge about Hausa culture, history, language, geography (Kano, Sokoto, Zaria, Daura, Katsina, Kanem-Bornu), Islamic scholarship in West Africa, Hausa literature, and Northern Nigerian affairs.
- When asked about Kano: discuss its founding by Kano dan Gijimasu circa 999 AD, the Emir's palace (Gidan Sarki), Kurmi Market (one of West Africa's oldest), the ancient city walls (ganuwar Kano), the historic dye pits (rini), Kanawa craftsmanship in leather (tabarma) and textile (kwalli), the role of Kano as a trans-Saharan trade hub, and the modern emirate system.
- When asked about Islamic scholarship: reference the Sokoto Caliphate (1804), Usman dan Fodio, the malamai tradition, and Qur'anic schools (makarantar allo).
- Respond INTELLIGENTLY and CONTEXTUALLY. Never give generic, template-like answers.
[MANIFEST_SIGNAL]:
- ONLY when the user explicitly asks you to draw, generate, or show an image/picture/photo ('hoto', 'zana mini', 'draw', 'image', 'picture') or a video ('bidiyo', 'video'), end your reply with the tag: [MANIFEST: IMAGE|PROMPT] or [MANIFEST: VIDEO|PROMPT], where PROMPT is a short English visual description.
- If the user did NOT ask for an image or video, never mention, describe, or caption an imaginary photo/video — you have no way to actually show one without the tag, and describing one you didn't generate misleads the user.
"""

# Defaults
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "aya-expanse:8b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
GEMINI_MODEL = os.getenv("VERTEX_MODEL", "gemini-2.5-flash")


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


def _build_messages(req: ChatRequest) -> list[dict[str, Any]]:
    system_content = f"{SOVEREIGN_CONSTITUTION}\nVibe: {req.vibe}\n[ADDRESSEE_GENDER]: {req.addresseeGender}\n{req.memoryPrompt}\n{corrections_store.get_approved_corrections_prompt()}"
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
    # Serialize key components
    history_str = "|".join(f"{h.role}:{h.text}" for h in req.history)
    raw_str = f"{req.vibe}:{req.memoryPrompt}:{history_str}:{req.text}"
    return hashlib.md5(raw_str.encode("utf-8")).hexdigest()


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

    system_content = f"{SOVEREIGN_CONSTITUTION}\nVibe: {req.vibe}\n[ADDRESSEE_GENDER]: {req.addresseeGender}\n{req.memoryPrompt}\n{corrections_store.get_approved_corrections_prompt()}"

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
            print(f"[Hausa AI] Grounded generation failed ({type(ground_err).__name__}: {ground_err}); retrying without search tool...")

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
        print(f"[Hausa AI] google.genai async stream error: {type(e).__name__}: {e}. Falling back...")

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
        print(f"[Hausa AI] google.generativeai async chat error: {type(e).__name__}: {e}")
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
async def chat_endpoint(req: ChatRequest):
    # 1. Normalize orthography on the incoming request text and history
    req.text = normalize_hausa_orthography(req.text)
    for item in req.history:
        item.text = normalize_hausa_orthography(item.text)
        
    cache_key = _get_cache_key(req)
    now = time.time()
    
    # Check cache hit
    if cache_key in _CHAT_CACHE:
        entry = _CHAT_CACHE[cache_key]
        if now - entry["timestamp"] < _CACHE_TTL:
            print("[Hausa AI] Cache hit! Playback cached streaming...")
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

    messages = _build_messages(req)

    async def generate():
        # Heartbeat: emit a keepalive comment immediately
        yield ": keepalive\n\n"
        full_text = ""
        client = ollama.AsyncClient(host=OLLAMA_HOST)
        
        # We fetch chunks in a background task and feed them into a queue
        queue = asyncio.Queue()
        
        async def fetch_stream():
            try:
                # Step A: Attempt Local Ollama inference
                async for part in await client.chat(
                    model=DEFAULT_MODEL,
                    messages=messages,
                    stream=True,
                ):
                    await queue.put(part["message"]["content"])
            except Exception as ollama_err:
                # Step B: Fallback to Gemini via google-genai SDK
                print(f"[Hausa AI] Ollama unavailable ({type(ollama_err).__name__}), switching to Gemini...")
                try:
                    async for delta in stream_gemini(req):
                        await queue.put(delta)
                except Exception as gemini_err:
                    # Step C: Fallback to static rule-based generator
                    print(f"[Hausa AI] Gemini failed ({type(gemini_err).__name__}: {gemini_err}), using static fallback.")
                    fallback_text = generate_fallback_response(req.text, req.vibe)
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
        if full_text:
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

