/** dictionaryService.ts — the Hausa<->English lexicon search, with an
 * offline IndexedDB fallback for when the network drops. */

import { withContributor, BACKEND_URL } from "./apiConfig.ts";
import { offlineKamus } from "./offlineKamusService.ts";

/** PUBLIC: search the dictionary (Robinson 1914 + Wiktionary + Newman 1977,
 * ~30,700 entries), same lexicon chat's hidden tool trigger already uses. */
export async function searchDictionary(query: string): Promise<{
  ready: boolean;
  results: { headword: string; translation: string; context: string; direction: string; source: string }[];
}> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/dictionary?q=${encodeURIComponent(query)}`, {
      headers: withContributor({}),
    });
    if (!res.ok) throw new Error(`dictionary lookup failed: ${res.status}`);
    const data = await res.json();
    // Fire-and-forget: keep the offline IndexedDB cache warm from every
    // successful online lookup, so it has something to serve next time
    // the network drops (see offlineKamusService.ts).
    void offlineKamus.cacheEntries(data.results ?? []);
    return data;
  } catch (err) {
    console.error("Dictionary lookup failed, falling back to offline cache:", err);
    const offlineResults = await offlineKamus.search(query);
    return { ready: offlineResults.length > 0, results: offlineResults };
  }
}
