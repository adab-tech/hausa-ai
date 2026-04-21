"""
/api/chat  — streaming text generation via Ollama.

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

import json
import os
import re
from typing import Any

import ollama
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter()

# ---------------------------------------------------------------------------
# Sovereign Constitution — identical to the original geminiService.ts prompt
# ---------------------------------------------------------------------------
SOVEREIGN_CONSTITUTION = """
[IDENTITY]: Vertex Sovereign (Nexus-7 Core).
[LINGUISTIC_CORE]: Standard Hausa (Fada).
[MANDATORY_SOCIAL_HIERARCHY]:
- All users must be addressed with the Plural of Respect (Ku/Su/Kun/Sun).
- Honorifics like 'Ranka ya dade' (to men) or 'Ranki ya dade' (to women) are required in greetings.
- 'Barka' or 'Sannu' must be followed by a formal inquiry into the user's wellbeing or family (Gaisuwa).
[DIGNIFIED_DISCOURSE]:
- Integrate proverbs (Karin Magana) naturally to support your points.
- Never use abbreviations. Use full formal Hausa orthography.
- Maintain 'Kunya' (Modesty): Use metaphors for sensitive or blunt topics.
[PROSODIC_HARDENING]:
- Use Litvinova's R-to-L Tonal Mapping.
- Mandatory Hooked Letters: ɓ, ɗ, ƙ, 'y.
[MANIFEST_SIGNAL]:
- Always generate text first.
- End with: [MANIFEST: IMAGE|PROMPT] or [MANIFEST: VIDEO|PROMPT].
"""

# Default model — change via OLLAMA_MODEL env var or docker-compose environment
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "aya-expanse:8b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")


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
    memoryPrompt: str = Field("", max_length=4_000)
    attachments: list[Attachment] = Field(default_factory=list, max_length=5)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_MANIFEST_RE = re.compile(r"\[MANIFEST:\s*(IMAGE|VIDEO)\s*\|\s*(.*?)\]", re.IGNORECASE)
_SANITIZE_RE = re.compile(r"\[MANIFEST:.*?\]|[*#$]")


def _sanitize(text: str) -> str:
    return _SANITIZE_RE.sub("", text).strip()


def _calculate_cultural_confidence(text: str) -> bool:
    score = 0
    if re.search(r"[ɓɗƙ'y]|ts", text):
        score += 40
    if re.search(r"\bkun\b|\bku\b|\bsu\b", text, re.IGNORECASE):
        score += 30
    if re.search(r"ranka ya dade|ranki ya dade|barka|gaisuwa", text, re.IGNORECASE):
        score += 30
    return score > 70


def _build_messages(req: ChatRequest) -> list[dict[str, Any]]:
    system_content = f"{SOVEREIGN_CONSTITUTION}\nVibe: {req.vibe}\n{req.memoryPrompt}"
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_content}]

    # Keep last 6 turns (context slicing — same as original)
    for item in req.history[-6:]:
        role = "user" if item.role == "user" else "assistant"
        messages.append({"role": role, "content": item.text})

    # Current user turn — include image attachments if the model supports vision
    images = [
        att.data.split("base64,")[1]
        for att in req.attachments
        if att.data and "base64," in att.data and att.mimeType.startswith("image/")
    ]
    if images:
        user_content = req.text
        messages.append({"role": "user", "content": user_content, "images": images})
    else:
        messages.append({"role": "user", "content": req.text})

    return messages


# ---------------------------------------------------------------------------
# Streaming endpoint
# ---------------------------------------------------------------------------
@router.post("/chat")
async def chat_endpoint(req: ChatRequest):
    messages = _build_messages(req)

    async def generate():
        full_text = ""
        client = ollama.AsyncClient(host=OLLAMA_HOST)
        try:
            async for part in await client.chat(
                model=DEFAULT_MODEL,
                messages=messages,
                stream=True,
            ):
                delta = part["message"]["content"]
                full_text += delta
                payload = json.dumps({"text": _sanitize(full_text), "isDone": False})
                yield f"data: {payload}\n\n"
        except Exception:
            error_text = (
                "Gafara, ranka ya dade. An samu tangarda a sashen Nexus-7. "
                "Amma kamar yadda karin magana ya nuna, 'Hargitsin duniya ba ya hana safiya wayewa'. "
                "Don Allah a sake gwadawa."
            )
            yield f"data: {json.dumps({'text': error_text, 'isDone': True, 'verified': False, 'error': 'LLM service unavailable'})}\n\n"
            return

        # Final done event
        manifest = _MANIFEST_RE.search(full_text)
        manifest_data = None
        if manifest:
            manifest_data = {"type": manifest.group(1).upper(), "prompt": manifest.group(2).strip()}

        yield f"data: {json.dumps({'text': _sanitize(full_text), 'isDone': True, 'verified': _calculate_cultural_confidence(full_text), 'manifest': manifest_data})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
