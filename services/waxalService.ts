/** waxalService.ts — browsing the WAXAL training corpus (admin-gated). */

import { BACKEND_URL } from "./apiConfig.ts";

// The /api/waxal/* endpoints are admin-gated. A 401 returns a truthy JSON
// body ({"detail": ...}) — passing that through as if it were data crashed
// the WAXAL tab's stats render to a black screen. Map 401 to an explicit
// {denied} marker and any other non-OK response to null.
export async function getWaxalStats(): Promise<any> {
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

export async function getWaxalSamples(
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

export function getWaxalAudioUrl(filename: string): string {
  // filename is e.g. "audio/Hausa_M4_001_0020.mp3"
  // We only need the basename for our endpoint
  const basename = filename.split("/").pop() || filename;
  return `${BACKEND_URL}/api/waxal/audio/${encodeURIComponent(basename)}`;
}
