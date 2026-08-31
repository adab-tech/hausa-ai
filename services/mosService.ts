/** mosService.ts — the MOS (Mean Opinion Score) listening test: a public,
 * anonymous session flow plus the admin results/decision endpoints. See
 * backend/mos_store.py / backend/routers/mos.py. */

import { BACKEND_URL, withContributor } from "./apiConfig.ts";

export type MosClip = {
  clip_id: string;
  condition: "murya" | "ground_truth";
  voice: string;
  sentence_id: string;
  text: string;
};

export type MosAnswer = {
  clip_id: string;
  condition: string;
  voice: string;
  sentence_id: string;
  score: number;
  intelligible: "yes" | "partial" | "no";
  replays: number;
};

// ── Public: listener session ───────────────────────────────────────────────
export async function getMosSession(): Promise<MosClip[] | null> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/mos/session`, { headers: withContributor({}) });
    if (!res.ok) return null;
    const data = await res.json();
    return data.clips ?? [];
  } catch (err) {
    console.error("Failed to fetch MOS session:", err);
    return null;
  }
}

export function mosAudioUrl(clipId: string): string {
  return `${BACKEND_URL}/api/mos/audio/${encodeURIComponent(clipId)}`;
}

export async function submitMosSession(
  sessionId: string,
  answers: MosAnswer[],
  region: string | null,
  nativeSpeaker: boolean
): Promise<boolean> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/mos/session`, {
      method: "POST",
      headers: withContributor({ "Content-Type": "application/json" }),
      body: JSON.stringify({ session_id: sessionId, region, native_speaker: nativeSpeaker, answers }),
    });
    return res.ok;
  } catch (err) {
    console.error("Failed to submit MOS session:", err);
    return false;
  }
}

// ── Admin: results + decisions ─────────────────────────────────────────────
export type MosStat = { mean: number | null; n: number; ci95: number | null };
export type MosAnalysis = {
  headline: string;
  verdict: "insufficient_data" | "close_to_human" | "meaningful_gap";
  gap: number | null;
  weak_voices: { voice: string; mean: number; n: number }[];
  intelligibility_pct_full: number | null;
  intelligibility_flag: boolean;
  min_trustworthy_n: number;
};
export type MosResults = {
  total_ratings: number;
  session_count: number;
  by_condition: Record<string, MosStat>;
  by_voice: Record<string, MosStat>;
  intelligibility: { yes: number; partial: number; no: number };
  analysis: MosAnalysis;
};
export type MosDecision = {
  id: number;
  verdict: string;
  note: string | null;
  total_ratings_at_time: number;
  murya_mean_at_time: number | null;
  ground_truth_mean_at_time: number | null;
  admin: string;
  created_at: number;
};

export async function getMosResults(): Promise<{ results: MosResults; decisions: MosDecision[] } | null> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/admin/mos/results`, { credentials: "include" });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error("Failed to fetch MOS results:", err);
    return null;
  }
}

export async function recordMosDecision(
  verdict: "approved_for_training" | "needs_more_data" | "rejected",
  note?: string
): Promise<boolean> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/admin/mos/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ verdict, note: note || null }),
    });
    return res.ok;
  } catch (err) {
    console.error("Failed to record MOS decision:", err);
    return false;
  }
}

export async function exportMosRatings(): Promise<boolean> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/admin/mos/export`, { credentials: "include" });
    if (!res.ok) return false;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "murya_mos_ratings.csv";
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
    return true;
  } catch (err) {
    console.error("Failed to export MOS ratings:", err);
    return false;
  }
}
