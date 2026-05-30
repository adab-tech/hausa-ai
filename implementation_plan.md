# Implementation Plan - GCP Vertex AI Fallback & Orthography Hardening

We are implementing a dual-layered fallback architecture and a pure-Python linguistic pipeline. This will allow the application to handle requests gracefully when the local Ollama service is unavailable, while enforcing cultural and phonetic sovereignty without relying on C++ compiled dependencies.

## User Review Required

> [!IMPORTANT]
> **No C++ Compiler Dependencies:** Due to the lack of Microsoft Visual C++ Build Tools on the target Windows machine and the use of Python 3.14 (where pre-built wheels for compiled packages like `editdistance` are not yet available), we will implement a pure-Python orthography normalization and R-to-L tonal mapping pipeline. This avoids compilation issues during setup while maintaining full phonetic processing accuracy.

> [!NOTE]
> **Vertex AI Integration:** The Vertex AI integration will use the authenticated Application Default Credentials (ADC) under your active project `studio-980910821-5b814`. It will call the REST API via Python's standard `google-auth` library and `httpx` to stream Gemini model responses.

---

## Proposed Changes

### Backend Component

We will refine the backend to parse user messages through the linguistic pipeline and introduce a Vertex AI client that acts as the primary fallback when Ollama is offline.

#### [MODIFY] [orthography.py](file:///c:/Users/Adamu/Desktop/hausa-ai-main/backend/orthography.py)
*   Expand the ASCII to Unicode mapping for Hausa hooked letters: handle complex edge cases and double consonants (e.g. `'y`, `ts`, `ƙ`, `ɗ`, `ɓ`).
*   Implement a rule-based **Litvinova Right-to-Left (R-to-L) Tonal Melody Mapping** algorithm. Since tone is not marked in standard orthography, we will write a function that segments words into light (CV) and heavy (CVV/CVC) syllables, then maps the tonal melody backwards from the end of each word. This will be used to generate tonal markers (e.g., `H` for high, `L` for low) to annotate the AI's response or inputs, which can be viewed in the "Axiom Trace" dashboard.

#### [MODIFY] [chat.py](file:///c:/Users/Adamu/Desktop/hausa-ai-main/backend/routers/chat.py)
*   Integrate `normalize_hausa_orthography` on user input so that inputs without hooks (e.g., `doki` -> `ɗoki`, `yan yanci` -> `ƴan ƴanci`) are automatically corrected before being sent to the LLM.
*   Implement the **Vertex AI Fallback**:
    *   Initialize `google.auth.default` to fetch default credentials and project ID.
    *   Create an async function `generate_vertex_ai_response` that uses `httpx.AsyncClient` to call the streaming Vertex AI Gemini endpoint (`gemini-1.5-flash` or `gemini-1.5-pro` under project `studio-980910821-5b814`).
    *   If Ollama raises an exception, the request will immediately fall back to Vertex AI.
    *   If both Ollama and Vertex AI fail (e.g. offline/no internet), it will gracefully fall back to the local rules-based `generate_fallback_response`.

---

## Verification Plan

### Automated Tests
*   Run a Python unit test script verifying the orthography normalizer and the R-to-L tone mapping output.
*   Run FastAPI server locally and verify that stopping Ollama triggers a streaming fallback request to Vertex AI.

### Manual Verification
*   Open the React app and send a message. Verify that the response still displays properly.
*   Turn off Ollama (or change `OLLAMA_HOST` to a dummy port) and send a message. Verify that the response is generated via Vertex AI.
*   Disconnect from the internet and verify that it falls back to the rules-based local response, maintaining the "Sovereign" tone and cultural formatting.
