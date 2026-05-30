"""
/api/chat  — streaming text generation via Ollama, falling back to Vertex AI / Google AI Studio.

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
from typing import Any, AsyncGenerator

import httpx
import ollama
import google.auth
import google.auth.transport.requests
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from routers.fallback import generate_fallback_response
from orthography import normalize_hausa_orthography, apply_tonal_heuristics

router = APIRouter()

# ---------------------------------------------------------------------------
# Sovereign Constitution — identical to the original geminiService.ts prompt
# ---------------------------------------------------------------------------
SOVEREIGN_CONSTITUTION = """
[IDENTITY]: Hausa AI (Nexus-7 Core).
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

# Defaults
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "aya-expanse:8b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")

# Vertex AI Settings
VERTEX_MODEL = os.getenv("VERTEX_MODEL", "gemini-1.5-flash")
VERTEX_REGION = os.getenv("VERTEX_REGION", "us-central1")

# Initialize GCP Application Default Credentials
try:
    credentials, project_id = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    if not project_id:
        project_id = os.getenv("GCP_PROJECT", "studio-980910821-5b814")
except Exception as e:
    credentials = None
    project_id = "studio-980910821-5b814"


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
    if re.search(r"[ɓɗƙƴ]|ts", text):
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


def get_vertex_token() -> str:
    if not credentials:
        raise RuntimeError("No Google Application Default Credentials (ADC) found.")
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    return credentials.token


def _build_vertex_payload(req: ChatRequest) -> dict:
    system_content = f"{SOVEREIGN_CONSTITUTION}\nVibe: {req.vibe}\n{req.memoryPrompt}"
    
    contents = []
    # Translate history
    for item in req.history[-6:]:
        role = "user" if item.role == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": item.text}]
        })
        
    # Translate current user turn
    user_parts = [{"text": req.text}]
    for att in req.attachments:
        if att.data and "base64," in att.data:
            base64_data = att.data.split("base64,")[1]
            user_parts.append({
                "inlineData": {
                    "mimeType": att.mimeType,
                    "data": base64_data
                }
            })
            
    contents.append({
        "role": "user",
        "parts": user_parts
    })
    
    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": system_content}]
        },
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2048
        }
    }
    return payload


async def stream_gcp_fallback(req: ChatRequest) -> AsyncGenerator[str, None]:
    """
    Tries multiple strategies to fall back to GCP/Gemini hosted generation:
      1. Google AI Studio with API Key (if GEMINI_API_KEY is configured).
      2. Vertex AI with Application Default Credentials (ADC).
      3. Google AI Studio with Application Default Credentials (ADC) if scopes are enabled.
    """
    # ─── Strategy 1: Google AI Studio via GEMINI_API_KEY ───────────────────
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        print("Fallback Strategy 1: Using GEMINI_API_KEY with Google AI Studio...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{VERTEX_MODEL}:streamGenerateContent?key={api_key}&alt=sse"
        headers = {"Content-Type": "application/json"}
        payload = _build_vertex_payload(req)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:].strip()
                                if not data_str:
                                    continue
                                event_data = json.loads(data_str)
                                candidates = event_data.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    if parts:
                                        text_chunk = parts[0].get("text", "")
                                        if text_chunk:
                                            yield text_chunk
                        return
                    else:
                        body = await response.aread()
                        print(f"AI Studio API Key connection failed (status {response.status_code}): {body.decode()[:200]}")
        except Exception as e:
            print(f"AI Studio API Key connection error: {e}")

    # ─── Strategy 2: Vertex AI via ADC ──────────────────────────────────────
    if credentials:
        print("Fallback Strategy 2: Attempting Vertex AI REST via ADC...")
        try:
            token = get_vertex_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            url = f"https://{VERTEX_REGION}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{VERTEX_REGION}/publishers/google/models/{VERTEX_MODEL}:streamGenerateContent?alt=sse"
            payload = _build_vertex_payload(req)
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:].strip()
                                if not data_str:
                                    continue
                                event_data = json.loads(data_str)
                                candidates = event_data.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    if parts:
                                        text_chunk = parts[0].get("text", "")
                                        if text_chunk:
                                            yield text_chunk
                        return
                    else:
                        body = await response.aread()
                        print(f"Vertex AI ADC connection failed (status {response.status_code}): {body.decode()[:200]}")
        except Exception as e:
            print(f"Vertex AI ADC connection error: {e}")

    # ─── Strategy 3: Google AI Studio via ADC ──────────────────────────────
    if credentials:
        print("Fallback Strategy 3: Attempting Google AI Studio REST via ADC...")
        try:
            token = get_vertex_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{VERTEX_MODEL}:streamGenerateContent?alt=sse"
            payload = _build_vertex_payload(req)
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:].strip()
                                if not data_str:
                                    continue
                                event_data = json.loads(data_str)
                                candidates = event_data.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    if parts:
                                        text_chunk = parts[0].get("text", "")
                                        if text_chunk:
                                            yield text_chunk
                        return
                    else:
                        body = await response.aread()
                        print(f"AI Studio ADC connection failed (status {response.status_code}): {body.decode()[:200]}")
        except Exception as e:
            print(f"AI Studio ADC connection error: {e}")

    raise RuntimeError("All cloud-based Gemini fallback generators failed or were unauthenticated.")


# ---------------------------------------------------------------------------
# Streaming endpoint
# ---------------------------------------------------------------------------
@router.post("/chat")
async def chat_endpoint(req: ChatRequest):
    # 1. Normalize orthography on the incoming request text and history
    req.text = normalize_hausa_orthography(req.text)
    for item in req.history:
        item.text = normalize_hausa_orthography(item.text)
        
    messages = _build_messages(req)

    async def generate():
        full_text = ""
        client = ollama.AsyncClient(host=OLLAMA_HOST)
        
        try:
            # Step A: Attempt Local Ollama inference
            async for part in await client.chat(
                model=DEFAULT_MODEL,
                messages=messages,
                stream=True,
            ):
                delta = part["message"]["content"]
                full_text += delta
                payload = json.dumps({"text": _sanitize(full_text), "isDone": False})
                yield f"data: {payload}\n\n"
                
        except Exception as ollama_err:
            # Step B: Fallback to GCP/Gemini Client strategies
            print(f"Ollama inference unavailable: {ollama_err}. Falling back to GCP/Gemini client...")
            try:
                async for delta in stream_gcp_fallback(req):
                    full_text += delta
                    payload = json.dumps({"text": _sanitize(full_text), "isDone": False})
                    yield f"data: {payload}\n\n"
            except Exception as vertex_err:
                # Step C: Fallback to static rule-based generator
                print(f"GCP/Gemini fallback failed: {vertex_err}. Triggering tier-3 local rules-based engine...")
                fallback_text = generate_fallback_response(req.text, req.vibe)
                words = fallback_text.split()
                accumulated = ""
                for i, word in enumerate(words):
                    accumulated += (word + (" " if i < len(words) - 1 else ""))
                    payload = json.dumps({"text": _sanitize(accumulated), "isDone": False})
                    yield f"data: {payload}\n\n"
                    await asyncio.sleep(0.06)
                
                manifest = _MANIFEST_RE.search(fallback_text)
                manifest_data = None
                if manifest:
                    manifest_data = {"type": manifest.group(1).upper(), "prompt": manifest.group(2).strip()}
                    
                # Print tonal diagnostics trace
                try:
                    tonal_trace = apply_tonal_heuristics(fallback_text)
                    print(f"[PROSODIC_TRACE] {tonal_trace}")
                except Exception:
                    pass
                    
                yield f"data: {json.dumps({'text': _sanitize(fallback_text), 'isDone': True, 'verified': _calculate_cultural_confidence(fallback_text), 'manifest': manifest_data, 'normalized': normalize_hausa_orthography(fallback_text), 'tone_mapped': apply_tonal_heuristics(fallback_text)})}\n\n"
                return

        # Log prosodic tonal trace for successful model generation
        try:
            tonal_trace = apply_tonal_heuristics(full_text)
            print(f"[PROSODIC_TRACE] {tonal_trace}")
        except Exception as tone_err:
            print(f"Failed to calculate prosodic trace: {tone_err}")

        # Final done event
        manifest = _MANIFEST_RE.search(full_text)
        manifest_data = None
        if manifest:
            manifest_data = {"type": manifest.group(1).upper(), "prompt": manifest.group(2).strip()}

        yield f"data: {json.dumps({'text': _sanitize(full_text), 'isDone': True, 'verified': _calculate_cultural_confidence(full_text), 'manifest': manifest_data, 'normalized': normalize_hausa_orthography(full_text), 'tone_mapped': apply_tonal_heuristics(full_text)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
