/**
 * localService.ts — Drop-in replacement for geminiService.ts
 *
 * All AI calls are routed to the self-hosted FastAPI backend at BACKEND_URL
 * (default http://localhost:8000) instead of the Google Gemini API.
 *
 * The public API surface is identical to the original GeminiService so that
 * App.tsx requires only minimal changes.
 */

import { Message, Attachment, Role, SovereignVibe } from "../types.ts";
import { learning } from "./learningService.ts";

// In production / Codespaces the env var VITE_BACKEND_URL can override this.
const BACKEND_URL =
  (import.meta as any).env?.VITE_BACKEND_URL ?? "http://localhost:8000";

// ─── SOVEREIGN CONSTITUTION (unchanged from original) ──────────────────────
const SOVEREIGN_CONSTITUTION = `
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
`;

// ─── Types returned by unifiedExchange ────────────────────────────────────
interface ExchangeChunk {
  text: string;
  attachments: Attachment[];
  groundingSources: any[];
  isDone: boolean;
  tier: string;
  verified: boolean;
}

class LocalService {
  // ── Text generation ──────────────────────────────────────────────────────
  async *unifiedExchange(
    text: string,
    history: Message[],
    userAttachments?: Attachment[],
    vibe: SovereignVibe = "Classic"
  ): AsyncGenerator<ExchangeChunk> {
    let finalAttachments: Attachment[] = [];
    let accumulatedText = "";

    const body = {
      text,
      history: history.slice(-6).map((m) => ({
        role: m.role === Role.user ? "user" : "assistant",
        text: m.text,
      })),
      vibe,
      memoryPrompt: learning.getMemoryPrompt(),
      attachments: (userAttachments ?? [])
        .filter((a) => a.data)
        .map((a) => ({ mimeType: a.mimeType, data: a.data! })),
    };

    try {
      const response = await fetch(`${BACKEND_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = JSON.parse(line.slice(6));
          accumulatedText = payload.text ?? accumulatedText;

          if (payload.isDone) {
            // Handle MANIFEST signal — request image/video from backend
            if (payload.manifest) {
              const { type, prompt } = payload.manifest;
              if (type === "VIDEO") {
                const uri = await this.generateVideo(prompt);
                if (uri)
                  finalAttachments.push({
                    name: "Sovereign Motion",
                    mimeType: "video/mp4",
                    uri,
                    type: "video",
                  });
              } else {
                const img = await this.generateImage(prompt, vibe);
                if (img)
                  finalAttachments.push({
                    name: "Sovereign Vision",
                    mimeType: "image/png",
                    data: img,
                    type: "image",
                  });
              }
            }
            yield {
              text: accumulatedText,
              attachments: finalAttachments,
              groundingSources: [],
              isDone: true,
              tier: "Pro",
              verified: payload.verified ?? false,
            };
          } else {
            yield {
              text: accumulatedText,
              attachments: finalAttachments,
              groundingSources: [],
              isDone: false,
              tier: "Pro",
              verified: false,
            };
          }
        }
      }
    } catch (err) {
      console.error("Sovereign Protocol Failure:", err);
      const errorText =
        "Gafara, ranka ya dade. An samu tangarda a sashen bincikenmu na 'Nexus-7'. " +
        "Amma kamar yadda karin magana ya nuna, 'Hargitsin duniya ba ya hana safiya wayewa'. " +
        "Don Allah a sake gwadawa.";
      yield {
        text: errorText,
        attachments: [],
        groundingSources: [],
        isDone: true,
        tier: "Pro",
        verified: false,
      };
    }
  }

  // ── Image generation ─────────────────────────────────────────────────────
  async generateImage(
    prompt: string,
    vibe: SovereignVibe
  ): Promise<string | null> {
    try {
      const res = await fetch(`${BACKEND_URL}/api/generate-image`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, vibe }),
      });
      const json = await res.json();
      return json.data ?? null;
    } catch {
      return null;
    }
  }

  // ── Video generation ─────────────────────────────────────────────────────
  async generateVideo(prompt: string): Promise<string | null> {
    try {
      const res = await fetch(`${BACKEND_URL}/api/generate-video`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      const json = await res.json();
      return json.uri ?? null;
    } catch {
      return null;
    }
  }

  // ── Live audio (bidirectional WebSocket) ─────────────────────────────────
  /**
   * Mirrors the original gemini.connectLive() API.
   * Returns an object with a .close() method.
   *
   * The backend WebSocket sends:
   *   { type: "audio", data: "<base64 pcm24k>" }  — spoken reply
   *   { type: "text",  data: "<transcript>" }       — debug transcript
   *   { type: "error", data: "<message>" }
   *
   * The frontend sends raw PCM-16 binary frames (16 kHz, mono) — same as before.
   */
  connectLive(callbacks: {
    onopen?: () => void;
    onmessage?: (msg: any) => void;
    onclose?: () => void;
    onerror?: (err: Event) => void;
  }): Promise<{ sendRealtimeInput: (p: { media: { data: string; mimeType: string } }) => void; close: () => void }> {
    const wsUrl = BACKEND_URL.replace(/^http/, "ws") + "/api/live";
    const ws = new WebSocket(wsUrl);
    ws.binaryType = "arraybuffer";

    ws.onopen = () => callbacks.onopen?.();
    ws.onclose = () => callbacks.onclose?.();
    ws.onerror = (e) => callbacks.onerror?.(e);

    ws.onmessage = (event) => {
      if (typeof event.data === "string") {
        const msg = JSON.parse(event.data);
        if (msg.type === "audio") {
          // Repackage as the shape the original onmessage handler expects
          callbacks.onmessage?.({
            serverContent: {
              modelTurn: {
                parts: [{ inlineData: { data: msg.data } }],
              },
            },
          });
        }
        // "text" and "error" messages are informational; ignore or log
      }
    };

    const session = {
      sendRealtimeInput: (payload: { media: { data: string; mimeType: string } }) => {
        if (ws.readyState !== WebSocket.OPEN) return;
        // Decode base64 PCM and send as binary
        const binary = atob(payload.media.data);
        const buf = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) buf[i] = binary.charCodeAt(i);
        ws.send(buf.buffer);
      },
      close: () => ws.close(),
    };

    return Promise.resolve(session);
  }
}

export const gemini = new LocalService();
