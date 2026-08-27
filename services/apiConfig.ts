/**
 * apiConfig.ts — shared backend URL resolution + anonymous contributor
 * identity, used by every domain service (chatService, adminService, etc.)
 * so none of them have to duplicate this logic.
 */

// In production / Codespaces the env var VITE_BACKEND_URL can override this.
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
export function withContributor(headers: Record<string, string> = {}): Record<string, string> {
  return { ...headers, "X-Contributor-Id": getContributorId() };
}
