/** visitorAnalyticsService.ts — privacy-preserving visit tracking (no IP;
 * geography by browser timezone; uniqueness by the anonymous contributor
 * id) and the admin-only view of it. */

import { BACKEND_URL, withContributor } from "./apiConfig.ts";

export async function recordVisit(): Promise<void> {
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

/** ADMIN. */
export async function getAnalytics(): Promise<any | null> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/admin/analytics`, { credentials: "include" });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error("Failed to fetch analytics:", err);
    return null;
  }
}
