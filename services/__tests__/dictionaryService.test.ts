import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// offlineKamusService.ts touches indexedDB at module load (its constructor
// calls this.init()); happy-dom doesn't implement IndexedDB, so the real
// module would throw on import. Mock it at the module boundary instead --
// this also lets each test control exactly what the "offline cache" holds,
// which is the actual thing under test here (the fallback branch).
vi.mock('../offlineKamusService.ts', () => ({
  offlineKamus: {
    cacheEntries: vi.fn().mockResolvedValue(undefined),
    search: vi.fn(),
  },
}));

import { searchDictionary } from '../dictionaryService.ts';
import { offlineKamus } from '../offlineKamusService.ts';

const mockEntry = { headword: 'ruwa', translation: 'water', context: 'N.M.', direction: 'ha-en', source: 'Newman (1977)' };

describe('searchDictionary', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('returns the online result and warms the offline cache on success', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({ ready: true, results: [mockEntry] }),
    });

    const result = await searchDictionary('ruwa');

    expect(result).toEqual({ ready: true, results: [mockEntry] });
    expect(offlineKamus.cacheEntries).toHaveBeenCalledWith([mockEntry]);
  });

  it('falls back to the offline cache when the network request fails', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('network down'));
    (offlineKamus.search as ReturnType<typeof vi.fn>).mockResolvedValue([mockEntry]);

    const result = await searchDictionary('ruwa');

    expect(result).toEqual({ ready: true, results: [mockEntry] });
    expect(offlineKamus.cacheEntries).not.toHaveBeenCalled();
  });

  it('falls back to the offline cache when the backend returns a non-OK status', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: false, status: 500 });
    (offlineKamus.search as ReturnType<typeof vi.fn>).mockResolvedValue([]);

    const result = await searchDictionary('ruwa');

    // ready:false is the signal DictionarySearch.tsx uses to show
    // "Ƙamus ba ya samuwa a yanzu" -- must stay false when there's
    // truly nothing to show, not just because the network failed.
    expect(result).toEqual({ ready: false, results: [] });
  });

  it('reports ready:false when both the network and the offline cache come up empty', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('network down'));
    (offlineKamus.search as ReturnType<typeof vi.fn>).mockResolvedValue([]);

    const result = await searchDictionary('zzz-not-a-word');

    expect(result.ready).toBe(false);
    expect(result.results).toEqual([]);
  });
});
