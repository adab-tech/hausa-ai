/** adminService.ts — admin session (cookie-based) and every moderation
 * action behind it: corrections, community Q&A, and pronunciation review
 * queues. See backend/admin_store.py. */

import { BACKEND_URL } from "./apiConfig.ts";

// ── Admin session ────────────────────────────────────────────────────────
export async function adminLogin(username: string, password: string): Promise<{ ok: true; username: string } | { ok: false; error: string }> {
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

/** Self-service password change (see backend/admin_store.py's
 * change_password). On success the backend invalidates every session for
 * this admin, including the one making this call -- the caller must
 * treat a successful response as "now logged out," not "still logged
 * in," and redirect to login. */
export async function changePassword(oldPassword: string, newPassword: string): Promise<{ ok: true } | { ok: false; error: string }> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/admin/change-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    });
    if (res.status === 401) {
      return { ok: false, error: "Kalmar sirri ta yanzu ba daidai ba ce. (Current password is incorrect.)" };
    }
    if (res.status === 422) {
      return { ok: false, error: "Sabuwar kalmar sirri dole ta kai haruffa 12 aƙalla. (New password must be at least 12 characters.)" };
    }
    if (!res.ok) {
      return { ok: false, error: "An samu kuskure. A sake gwadawa. (Something went wrong. Try again.)" };
    }
    return { ok: true };
  } catch (err) {
    console.error("Change password failed:", err);
    return { ok: false, error: "An samu kuskure wajen haɗawa da uwar garke. (Could not reach the server.)" };
  }
}

export async function adminLogout(): Promise<void> {
  try {
    await fetch(`${BACKEND_URL}/api/admin/logout`, { method: "POST", credentials: "include" });
  } catch (err) {
    console.error("Admin logout failed:", err);
  }
}

export async function adminMe(): Promise<string | null> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/admin/me`, { credentials: "include" });
    if (!res.ok) return null;
    const data = await res.json();
    return data.username;
  } catch {
    return null;
  }
}

/** Unified audit trail (who approved/rejected/deleted what, when)
 * across corrections/pronunciation/Q&A review — see admin_audit_store.py. */
export async function getAuditLog(surface?: "correction" | "pronunciation" | "qa"): Promise<
  { id: number; admin: string; action: string; surface: string; target_id: string | null; detail: string | null; created_at: number }[] | null
> {
  try {
    const q = surface ? `?surface=${surface}` : "";
    const res = await fetch(`${BACKEND_URL}/api/admin/audit-log${q}`, { credentials: "include" });
    if (!res.ok) return null;
    const data = await res.json();
    return data.items ?? [];
  } catch (err) {
    console.error("Failed to fetch audit log:", err);
    return null;
  }
}

// ── Corrections review queue (real admin session, not a shared key) ───────
export async function getCorrections(status: "pending" | "approved" | "rejected"): Promise<any[] | null> {
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

export async function reviewCorrection(id: string, action: "approve" | "reject"): Promise<boolean> {
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

// ── Community Hausa Q&A (native-written instruction data) ─────────────────
/** ADMIN: list Q&A items (+ counts). */
export async function getQA(status?: "pending" | "approved" | "rejected"): Promise<{ items: any[]; counts: any } | null> {
  try {
    const q = status ? `?status=${status}` : "";
    const res = await fetch(`${BACKEND_URL}/api/admin/qa${q}`, { credentials: "include" });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) { console.error("Failed to fetch Q&A:", err); return null; }
}

/** ADMIN: approve / reject a Q&A item. */
export async function setQAStatus(id: number, status: "pending" | "approved" | "rejected"): Promise<boolean> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/admin/qa/${id}/status`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      credentials: "include", body: JSON.stringify({ status }),
    });
    return res.ok;
  } catch (err) { console.error("Failed to set Q&A status:", err); return false; }
}

/** ADMIN: delete a Q&A item. */
export async function deleteQA(id: number): Promise<boolean> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/admin/qa/${id}`, { method: "DELETE", credentials: "include" });
    return res.ok;
  } catch (err) { console.error("Failed to delete Q&A:", err); return false; }
}

/** ADMIN: download approved Q&A as instruction JSONL for the training mix. */
export async function exportQA(): Promise<boolean> {
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

// ── Pronunciation corrections (human-in-the-loop TTS) ─────────────────────
/** ADMIN: list correction items (+ counts) for the review dashboard. */
export async function getPronunciations(status?: "pending" | "approved" | "rejected"): Promise<{ items: any[]; counts: any } | null> {
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
export async function submitPronunciation(text: string, speakerId: number | null, audio: Blob, note?: string): Promise<boolean> {
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
export async function recordPronunciation(id: number, audio: Blob): Promise<boolean> {
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
export async function setPronunciationStatus(id: number, status: "pending" | "approved" | "rejected"): Promise<boolean> {
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
export async function deletePronunciation(id: number): Promise<boolean> {
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
export async function exportPronunciationCorpus(): Promise<boolean> {
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
export async function pronunciationAudioUrl(id: number): Promise<string | null> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/admin/pronunciation/${id}/audio`, { credentials: "include" });
    if (!res.ok) return null;
    return URL.createObjectURL(await res.blob());
  } catch (err) {
    console.error("Failed to fetch correction audio:", err);
    return null;
  }
}
