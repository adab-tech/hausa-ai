/**
 * localService.ts — Drop-in replacement for geminiService.ts
 *
 * All AI calls are routed to the self-hosted FastAPI backend at BACKEND_URL
 * (default http://localhost:8000) instead of the Google Gemini API.
 *
 * The public API surface is identical to the original GeminiService so that
 * App.tsx requires only minimal changes.
 */

import { Message, Attachment, Role, SovereignVibe, AddresseeGender } from "../types.ts";
import { learning } from "./learningService.ts";

// In production / Codespaces the env var VITE_BACKEND_URL can override this.
// Exported so the UI can display the real backend host instead of a hardcoded one.
export const BACKEND_URL = (
  (import.meta as any).env?.VITE_BACKEND_URL ??
  (typeof window !== "undefined" && window.location.port === "3000"
    ? "http://127.0.0.1:8000"
    : typeof window !== "undefined"
    ? window.location.origin
    : "http://127.0.0.1:8000")
).replace("localhost", "127.0.0.1");

// ─── Anonymous contributor identity (Level 1 — no login wall) ──────────────
// A PII-free device token, generated once and kept in localStorage. Sent as
// the X-Contributor-Id header (or a contributor_id query param where headers
// aren't possible — the TTS <audio> element and the live WebSocket) so the
// backend can rate-limit per device instead of per shared IP (carrier-grade
// NAT is the norm across the Sahel) and attribute feedback/corrections
// without anyone logging in. Identifies a device, not a person.
const _CONTRIBUTOR_KEY = "murya_contributor_id";
let _cachedContributorId: string | null = null;

function _uuidv4(): string {
  // Fallback for environments without crypto.randomUUID (older WebViews).
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

export function getContributorId(): string {
  if (_cachedContributorId) return _cachedContributorId;
  const make = () => globalThis.crypto?.randomUUID?.() ?? _uuidv4();
  try {
    let id = localStorage.getItem(_CONTRIBUTOR_KEY);
    if (!id) {
      id = make();
      localStorage.setItem(_CONTRIBUTOR_KEY, id);
    }
    _cachedContributorId = id;
  } catch {
    // localStorage blocked (private mode / SSR): use an in-memory id so the
    // token is at least stable for this page's lifetime.
    _cachedContributorId = make();
  }
  return _cachedContributorId;
}

/** Merge the contributor-id header into a headers object for fetch(). */
function withContributor(headers: Record<string, string> = {}): Record<string, string> {
  return { ...headers, "X-Contributor-Id": getContributorId() };
}

// ─── SOVEREIGN CONSTITUTION (unchanged from original) ──────────────────────
const SOVEREIGN_CONSTITUTION = `
[IDENTITY]: Murya, a sovereign Hausa AI.
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
[MANIFEST_SIGNAL]:
- ONLY when the user explicitly asks you to draw, generate, or show an image/picture/photo ('hoto', 'zana mini', 'draw', 'image', 'picture') or a video ('bidiyo', 'video'), end your reply with the tag: [MANIFEST: IMAGE|PROMPT] or [MANIFEST: VIDEO|PROMPT], where PROMPT is a short English visual description.
- If the user did NOT ask for an image or video, never mention, describe, or caption an imaginary photo/video — you have no way to actually show one without the tag, and describing one you didn't generate misleads the user.
`;

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

class LocalService {
  // ── Text generation ──────────────────────────────────────────────────────
  async *unifiedExchange(
    text: string,
    history: Message[],
    userAttachments?: Attachment[],
    vibe: SovereignVibe = "Classic",
    addresseeGender: AddresseeGender = "unspecified",
    mode: "assistant" | "tutor" = "assistant"
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
  connectLive(
    speakerId: number | null,
    callbacks: {
      onopen?: () => void;
      onmessage?: (msg: any) => void;
      onclose?: () => void;
      onerror?: (err: Event) => void;
    },
    addresseeGender: AddresseeGender = "unspecified"
  ): Promise<{ sendRealtimeInput: (p: { media: { data: string; mimeType: string } }) => void; close: () => void }> {
    const params = new URLSearchParams();
    if (speakerId !== null) params.set("speaker_id", String(speakerId));
    params.set("addressee_gender", addresseeGender);
    // Browser WebSocket can't set custom headers, so the contributor id rides
    // as a query param (backend reads it from either place, see contributor.py).
    params.set("contributor_id", getContributorId());
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
      close: () => ws.close(),
    };

    return Promise.resolve(session);
  }

  // ── WAXAL Dataset endpoints ──────────────────────────────────────────────
  // The /api/waxal/* endpoints are admin-gated. A 401 returns a truthy JSON
  // body ({"detail": ...}) — passing that through as if it were data crashed
  // the WAXAL tab's stats render to a black screen. Map 401 to an explicit
  // {denied} marker and any other non-OK response to null.
  async getWaxalStats(): Promise<any> {
    try {
      const res = await fetch(`${BACKEND_URL}/api/waxal/stats`, { credentials: "include" });
      if (res.status === 401) return { denied: true };
      if (!res.ok) return null;
      return await res.json();
    } catch (err) {
      console.error("Failed to fetch WAXAL stats:", err);
      return null;
    }
  }

  async getWaxalSamples(
    page: number,
    pageSize: number,
    speakerId?: string,
    gender?: string,
    query?: string
  ): Promise<any> {
    try {
      let url = `${BACKEND_URL}/api/waxal/samples?page=${page}&page_size=${pageSize}`;
      if (speakerId) url += `&speaker_id=${encodeURIComponent(speakerId)}`;
      if (gender) url += `&gender=${encodeURIComponent(gender)}`;
      if (query) url += `&query=${encodeURIComponent(query)}`;

      const res = await fetch(url, { credentials: "include" });
      if (!res.ok) return null;
      return await res.json();
    } catch (err) {
      console.error("Failed to fetch WAXAL samples:", err);
      return null;
    }
  }

  getWaxalAudioUrl(filename: string): string {
    // filename is e.g. "audio/Hausa_M4_001_0020.mp3"
    // We only need the basename for our endpoint
    const basename = filename.split("/").pop() || filename;
    return `${BACKEND_URL}/api/waxal/audio/${encodeURIComponent(basename)}`;
  }

  getTtsUrl(text: string, speakerId: number | null): string {
    const spkQuery = speakerId !== null ? `&speaker_id=${speakerId}` : "";
    // <audio src> can't set headers, so the contributor id rides as a query
    // param — the backend reads it from either place (see contributor.py).
    const cidQuery = `&contributor_id=${encodeURIComponent(getContributorId())}`;
    return `${BACKEND_URL}/api/tts?text=${encodeURIComponent(text)}${spkQuery}${cidQuery}`;
  }

  // ── Feedback ──────────────────────────────────────────────────────────────
  async recordFeedback(messageId: string, type: "up" | "down", text: string, correction?: string): Promise<void> {
    try {
      await fetch(`${BACKEND_URL}/api/feedback`, {
        method: "POST",
        headers: withContributor({ "Content-Type": "application/json" }),
        body: JSON.stringify({ messageId, type, text, correction: correction ?? "" }),
      });
    } catch (err) {
      console.error("Failed to record feedback:", err);
    }
  }

  // ── Document translate / summarize (one-shot; streams the result) ─────────
  async *streamDocument(
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

  // ── Visitor analytics (privacy-preserving: no IP; geography by browser
  // timezone; uniqueness by the anonymous contributor id) ───────────────────
  async recordVisit(): Promise<void> {
    try {
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
      await fetch(`${BACKEND_URL}/api/analytics/visit`, {
        method: "POST",
        headers: withContributor({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          timezone,
          lang: navigator.language || "",
          path: typeof location !== "undefined" ? location.pathname : "/",
        }),
        keepalive: true,
      });
    } catch {
      // Analytics must never affect the user experience.
    }
  }

  async getAnalytics(): Promise<any | null> {
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/analytics`, { credentials: "include" });
      if (!res.ok) return null;
      return await res.json();
    } catch (err) {
      console.error("Failed to fetch analytics:", err);
      return null;
    }
  }

  // ── Admin session (cookie-based; see backend/admin_store.py) ──────────────
  async adminLogin(username: string, password: string): Promise<{ ok: true; username: string } | { ok: false; error: string }> {
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) return { ok: false, error: "Sunan mai amfani ko kalmar sirri ba daidai ba." };
      const data = await res.json();
      return { ok: true, username: data.username };
    } catch (err) {
      console.error("Admin login failed:", err);
      return { ok: false, error: "An samu kuskure wajen haɗawa da uwar garke." };
    }
  }

  async adminLogout(): Promise<void> {
    try {
      await fetch(`${BACKEND_URL}/api/admin/logout`, { method: "POST", credentials: "include" });
    } catch (err) {
      console.error("Admin logout failed:", err);
    }
  }

  async adminMe(): Promise<string | null> {
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/me`, { credentials: "include" });
      if (!res.ok) return null;
      const data = await res.json();
      return data.username;
    } catch (err) {
      return null;
    }
  }

  // ── Corrections review queue (real admin session, not a shared key) ───────
  async getCorrections(status: "pending" | "approved" | "rejected"): Promise<any[] | null> {
    try {
      const res = await fetch(`${BACKEND_URL}/api/corrections?status=${status}`, {
        credentials: "include",
      });
      if (!res.ok) return null;
      return await res.json();
    } catch (err) {
      console.error("Failed to fetch corrections:", err);
      return null;
    }
  }

  async reviewCorrection(id: string, action: "approve" | "reject"): Promise<boolean> {
    try {
      const res = await fetch(`${BACKEND_URL}/api/corrections/${id}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ action }),
      });
      return res.ok;
    } catch (err) {
      console.error("Failed to review correction:", err);
      return false;
    }
  }

  async getFeedbackStats(): Promise<{ up: number; down: number; total: number } | null> {
    try {
      const res = await fetch(`${BACKEND_URL}/api/feedback/stats`);
      return await res.json();
    } catch (err) {
      console.error("Failed to fetch feedback stats:", err);
      return null;
    }
  }

  // ── Pronunciation corrections (human-in-the-loop TTS) ─────────────────────
  /** PUBLIC: a user reports a mispronunciation for a reviewer to fix. */
  async flagPronunciation(text: string, speakerId: number | null = null, note?: string): Promise<boolean> {
    try {
      const res = await fetch(`${BACKEND_URL}/api/pronunciation/flag`, {
        method: "POST",
        headers: withContributor({ "Content-Type": "application/json" }),
        credentials: "include",
        body: JSON.stringify({ text, speaker_id: speakerId, note }),
      });
      return res.ok;
    } catch (err) {
      console.error("Failed to flag pronunciation:", err);
      return false;
    }
  }

  // ── Community Hausa Q&A (native-written instruction data) ─────────────────
  /** PUBLIC: contribute a Hausa question + answer. Lands pending for owner approval. */
  async submitQA(question: string, answer: string, topic?: string): Promise<boolean> {
    try {
      const res = await fetch(`${BACKEND_URL}/api/qa/submit`, {
        method: "POST",
        headers: withContributor({ "Content-Type": "application/json" }),
        credentials: "include",
        body: JSON.stringify({ question, answer, topic }),
      });
      return res.ok;
    } catch (err) { console.error("Failed to submit Q&A:", err); return false; }
  }

  /** ADMIN: list Q&A items (+ counts). */
  async getQA(status?: "pending" | "approved" | "rejected"): Promise<{ items: any[]; counts: any } | null> {
    try {
      const q = status ? `?status=${status}` : "";
      const res = await fetch(`${BACKEND_URL}/api/admin/qa${q}`, { credentials: "include" });
      if (!res.ok) return null;
      return await res.json();
    } catch (err) { console.error("Failed to fetch Q&A:", err); return null; }
  }

  /** ADMIN: approve / reject a Q&A item. */
  async setQAStatus(id: number, status: "pending" | "approved" | "rejected"): Promise<boolean> {
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/qa/${id}/status`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        credentials: "include", body: JSON.stringify({ status }),
      });
      return res.ok;
    } catch (err) { console.error("Failed to set Q&A status:", err); return false; }
  }

  /** ADMIN: delete a Q&A item. */
  async deleteQA(id: number): Promise<boolean> {
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/qa/${id}`, { method: "DELETE", credentials: "include" });
      return res.ok;
    } catch (err) { console.error("Failed to delete Q&A:", err); return false; }
  }

  /** ADMIN: download approved Q&A as instruction JSONL for the training mix. */
  async exportQA(): Promise<boolean> {
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/qa/export`, { credentials: "include" });
      if (!res.ok) return false;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "murya_community_qa.jsonl";
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
      return true;
    } catch (err) { console.error("Failed to export Q&A:", err); return false; }
  }

  /** PUBLIC: a user records the correct pronunciation of a word/phrase (+ optional
   * note). Lands pending for the owner to approve — never served without approval. */
  async submitUserPronunciation(text: string, speakerId: number | null, audio: Blob, note?: string): Promise<boolean> {
    try {
      const fd = new FormData();
      fd.append("text", text);
      if (speakerId !== null && speakerId !== undefined) fd.append("speaker_id", String(speakerId));
      if (note) fd.append("note", note);
      fd.append("audio", audio, "correction.webm");
      const res = await fetch(`${BACKEND_URL}/api/pronunciation/submit`, {
        method: "POST", headers: withContributor({}), credentials: "include", body: fd,
      });
      return res.ok;
    } catch (err) {
      console.error("Failed to submit user pronunciation:", err);
      return false;
    }
  }

  /** ADMIN: list correction items (+ counts) for the review dashboard. */
  async getPronunciations(status?: "pending" | "approved" | "rejected"): Promise<{ items: any[]; counts: any } | null> {
    try {
      const q = status ? `?status=${status}` : "";
      const res = await fetch(`${BACKEND_URL}/api/admin/pronunciation${q}`, { credentials: "include" });
      if (!res.ok) return null;
      return await res.json();
    } catch (err) {
      console.error("Failed to fetch pronunciations:", err);
      return null;
    }
  }

  /** ADMIN: record a NEW correction (the correct way to say `text`). */
  async submitPronunciation(text: string, speakerId: number | null, audio: Blob, note?: string): Promise<boolean> {
    try {
      const fd = new FormData();
      fd.append("text", text);
      if (speakerId !== null && speakerId !== undefined) fd.append("speaker_id", String(speakerId));
      if (note) fd.append("note", note);
      fd.append("audio", audio, "correction.webm");
      const res = await fetch(`${BACKEND_URL}/api/admin/pronunciation`, {
        method: "POST", credentials: "include", body: fd,
      });
      return res.ok;
    } catch (err) {
      console.error("Failed to submit pronunciation:", err);
      return false;
    }
  }

  /** ADMIN: attach a recording to an existing flagged item and approve it. */
  async recordPronunciation(id: number, audio: Blob): Promise<boolean> {
    try {
      const fd = new FormData();
      fd.append("audio", audio, "correction.webm");
      const res = await fetch(`${BACKEND_URL}/api/admin/pronunciation/${id}/record`, {
        method: "POST", credentials: "include", body: fd,
      });
      return res.ok;
    } catch (err) {
      console.error("Failed to record pronunciation:", err);
      return false;
    }
  }

  /** ADMIN: approve / reject. */
  async setPronunciationStatus(id: number, status: "pending" | "approved" | "rejected"): Promise<boolean> {
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/pronunciation/${id}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ status }),
      });
      return res.ok;
    } catch (err) {
      console.error("Failed to set pronunciation status:", err);
      return false;
    }
  }

  /** ADMIN: delete a correction. */
  async deletePronunciation(id: number): Promise<boolean> {
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/pronunciation/${id}`, {
        method: "DELETE", credentials: "include",
      });
      return res.ok;
    } catch (err) {
      console.error("Failed to delete pronunciation:", err);
      return false;
    }
  }

  /** ADMIN: download all approved corrections as a training-ready ZIP. */
  async exportPronunciationCorpus(): Promise<boolean> {
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/pronunciation/export`, { credentials: "include" });
      if (!res.ok) return false;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "murya_pronunciation_corpus.zip";
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      return true;
    } catch (err) {
      console.error("Failed to export corpus:", err);
      return false;
    }
  }

  /** ADMIN: fetch a correction's audio (with the session cookie) as a playable object URL. */
  async pronunciationAudioUrl(id: number): Promise<string | null> {
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/pronunciation/${id}/audio`, { credentials: "include" });
      if (!res.ok) return null;
      return URL.createObjectURL(await res.blob());
    } catch (err) {
      console.error("Failed to fetch correction audio:", err);
      return null;
    }
  }

  // ── Deep research (Tavily Research — multi-step, cited answers) ───────────
  /** Start a deep-research task. Returns the request_id to poll, or null on
   * failure (unconfigured server, rate limit, etc). */
  async startResearch(query: string, model: "mini" | "pro" | "auto" = "auto"): Promise<string | null> {
    try {
      const res = await fetch(`${BACKEND_URL}/api/research/start`, {
        method: "POST",
        headers: withContributor({ "Content-Type": "application/json" }),
        body: JSON.stringify({ query, model }),
      });
      if (!res.ok) return null;
      const data = await res.json();
      return data.request_id ?? null;
    } catch (err) {
      console.error("Failed to start research:", err);
      return null;
    }
  }

  /** Poll a research task once. Returns Tavily's raw status dict, or null on
   * failure (unknown id, network error). */
  async getResearchStatus(requestId: string): Promise<any | null> {
    try {
      const res = await fetch(`${BACKEND_URL}/api/research/${requestId}`, {
        headers: withContributor({}),
      });
      if (!res.ok) return null;
      return await res.json();
    } catch (err) {
      console.error("Failed to poll research:", err);
      return null;
    }
  }
}

export const gemini = new LocalService();
