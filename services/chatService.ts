/**
 * chatService.ts — the core AI interaction surface: text chat (streaming),
 * image/video generation, live voice (bidirectional WebSocket), and
 * document translate/summarize.
 */

import { Message, Attachment, Role, SovereignVibe, AddresseeGender } from "../types.ts";
import { learning } from "./learningService.ts";
import { BACKEND_URL, withContributor, getContributorId } from "./apiConfig.ts";

// ─── Types returned by unifiedExchange ────────────────────────────────────
interface ExchangeChunk {
  text: string;
  attachments: Attachment[];
  groundingSources: any[];
  isDone: boolean;
  tier: string;
  verified: boolean;
  normalized?: string;
  toneMapped?: string;
}

// ── Text generation ──────────────────────────────────────────────────────
export async function* unifiedExchange(
  text: string,
  history: Message[],
  userAttachments?: Attachment[],
  vibe: SovereignVibe = "Classic",
  addresseeGender: AddresseeGender = "unspecified",
  mode: "assistant" | "tutor" = "assistant"
): AsyncGenerator<ExchangeChunk> {
  const finalAttachments: Attachment[] = [];
  let accumulatedText = "";

  const body = {
    text,
    history: history.slice(-6).map((m) => ({
      role: m.role === Role.user ? "user" : "assistant",
      text: m.text,
    })),
    vibe,
    addresseeGender,
    mode,
    memoryPrompt: learning.getMemoryPrompt(),
    attachments: (userAttachments ?? [])
      .filter((a) => a.data)
      .map((a) => ({ mimeType: a.mimeType, data: a.data! })),
  };

  try {
    const response = await fetch(`${BACKEND_URL}/api/chat`, {
      method: "POST",
      headers: withContributor({ "Content-Type": "application/json" }),
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`Sovereign server returned status ${response.status}`);
    }

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
              const uri = await generateVideo(prompt);
              if (uri)
                finalAttachments.push({
                  name: "Sovereign Motion",
                  mimeType: "video/mp4",
                  uri,
                  type: "video",
                });
            } else {
              const img = await generateImage(prompt, vibe);
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
            normalized: payload.normalized,
            toneMapped: payload.tone_mapped,
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
      "Gafara, ranka ya dade. An samu tangarda a sashen bincikenmu na 'Murya'. " +
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
export async function generateImage(
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
export async function generateVideo(prompt: string): Promise<string | null> {
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
export async function connectLive(
  speakerId: number | null,
  callbacks: {
    onopen?: () => void;
    onmessage?: (msg: any) => void;
    onclose?: () => void;
    onerror?: (err: Event) => void;
  },
  addresseeGender: AddresseeGender = "unspecified"
): Promise<{
  sendRealtimeInput: (p: { media: { data: string; mimeType: string } }) => void;
  setAssistantSpeaking: (speaking: boolean) => void;
  close: () => void;
}> {
  const params = new URLSearchParams();
  if (speakerId !== null) params.set("speaker_id", String(speakerId));
  params.set("addressee_gender", addresseeGender);
  // Browser WebSocket can't set custom headers, so the contributor id rides
  // as a query param (backend reads it from either place, see contributor.py).
  params.set("contributor_id", getContributorId());

  // A build-time API key means this is talking to a private/firewalled
  // deployment (see backend/auth.py, backend/docs/deployment.md). The
  // public default (this key unset) skips this entirely -- no extra round
  // trip before every live-voice session for a secret that doesn't exist
  // in that mode. When it IS set, exchange it for a short-lived, single-
  // use ticket over a normal header-authenticated HTTP call rather than
  // putting the standing key itself in the WebSocket URL, where it would
  // sit in plaintext in every proxy access log for as long as the
  // deployment runs (see auth.issue_live_ticket's docstring).
  const privateApiKey = (import.meta as any).env?.VITE_API_KEY;
  if (privateApiKey) {
    const ticketRes = await fetch(`${BACKEND_URL}/api/live/ticket`, {
      method: "POST",
      headers: { "X-API-Key": privateApiKey },
    });
    if (!ticketRes.ok) {
      throw new Error("Could not obtain a live-session ticket (check VITE_API_KEY).");
    }
    const { ticket } = await ticketRes.json();
    params.set("ticket", ticket);
  }

  const wsUrl = BACKEND_URL.replace(/^http/, "ws") + `/api/live?${params.toString()}`;
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
      } else if (msg.type === "user_transcript") {
        callbacks.onmessage?.({
          text: msg.data,
          isUser: true,
        });
      } else if (msg.type === "text") {
        callbacks.onmessage?.({
          text: msg.data,
          isUser: false,
          normalized: msg.normalized,
          toneMapped: msg.tone_mapped,
        });
      }
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
    // Server-side backstop against the "assistant hears itself" self-echo
    // loop: tells the backend, via a small JSON control frame, when this
    // reply's TTS is scheduled to be audible so it can drop any leaked
    // mic audio itself -- independent of whatever the client's own
    // half-duplex mute window did or didn't catch (see the matching
    // comment in backend/routers/audio.py's live_endpoint).
    setAssistantSpeaking: (speaking: boolean) => {
      if (ws.readyState !== WebSocket.OPEN) return;
      ws.send(JSON.stringify({ type: "assistant_speaking", value: speaking }));
    },
    close: () => ws.close(),
  };

  return session;
}

export function getTtsUrl(text: string, speakerId: number | null): string {
  const spkQuery = speakerId !== null ? `&speaker_id=${speakerId}` : "";
  // <audio src> can't set headers, so the contributor id rides as a query
  // param — the backend reads it from either place (see contributor.py).
  const cidQuery = `&contributor_id=${encodeURIComponent(getContributorId())}`;
  return `${BACKEND_URL}/api/tts?text=${encodeURIComponent(text)}${spkQuery}${cidQuery}`;
}

// ── Document translate / summarize (one-shot; streams the result) ─────────
export async function* streamDocument(
  text: string,
  action: "translate" | "summarize",
  target: "ha" | "en"
): AsyncGenerator<{ text: string; isDone: boolean; error?: string }> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/document`, {
      method: "POST",
      headers: withContributor({ "Content-Type": "application/json" }),
      body: JSON.stringify({ text, action, target }),
    });
    if (!res.ok || !res.body) {
      yield { text: "", isDone: true, error: "An samu kuskure. A sake gwadawa." };
      return;
    }
    const reader = res.body.getReader();
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
        yield JSON.parse(line.slice(6));
      }
    }
  } catch (err) {
    console.error("Document task failed:", err);
    yield { text: "", isDone: true, error: "An samu kuskure wajen haɗawa da uwar garke." };
  }
}
