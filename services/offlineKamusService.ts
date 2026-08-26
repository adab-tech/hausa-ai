/**
 * offlineKamusService.ts — IndexedDB local cache for the 30k+ Hausa Ƙamus
 *
 * Ensures full dictionary functionality continues working across the Sahel
 * even when cellular/wifi connections drop completely.
 */

export interface KamusEntry {
  headword: string;
  translation: string;
  context: string;
  direction: string;
  source: string;
}

const DB_NAME = 'MuryaKamusDB';
const DB_VERSION = 1;
const STORE_NAME = 'entries';

class OfflineKamusService {
  private db: IDBDatabase | null = null;
  private isReady = false;

  constructor() {
    this.init();
  }

  private init() {
    if (typeof window === 'undefined' || !('indexedDB' in window)) return;

    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event: any) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'headword' });
        store.createIndex('headword', 'headword', { unique: false });
        store.createIndex('translation', 'translation', { unique: false });
      }
    };

    request.onsuccess = (event: any) => {
      this.db = event.target.result;
      this.isReady = true;
    };

    request.onerror = (err) => {
      console.warn('Murya Offline Ƙamus IndexedDB open error:', err);
    };
  }

  /** Cache newly fetched results from the server into IndexedDB */
  async cacheEntries(entries: KamusEntry[]): Promise<void> {
    if (!this.db || !entries || entries.length === 0) return;

    return new Promise((resolve) => {
      try {
        const tx = this.db!.transaction(STORE_NAME, 'readwrite');
        const store = tx.objectStore(STORE_NAME);
        entries.forEach((entry) => {
          store.put(entry);
        });
        tx.oncomplete = () => resolve();
        tx.onerror = () => resolve();
      } catch (e) {
        resolve();
      }
    });
  }

  /** Search local IndexedDB when device is offline */
  async search(query: string): Promise<KamusEntry[]> {
    if (!this.db || !query.trim()) return [];

    const q = query.trim().toLowerCase();

    return new Promise((resolve) => {
      try {
        const tx = this.db!.transaction(STORE_NAME, 'readonly');
        const store = tx.objectStore(STORE_NAME);
        const request = store.getAll();

        request.onsuccess = () => {
          const all: KamusEntry[] = request.result || [];
          const matches = all.filter((item) => {
            const hw = (item.headword || '').toLowerCase();
            const tr = (item.translation || '').toLowerCase();
            return hw.includes(q) || tr.includes(q);
          }).slice(0, 30);
          resolve(matches);
        };

        request.onerror = () => resolve([]);
      } catch (e) {
        resolve([]);
      }
    });
  }
}

export const offlineKamus = new OfflineKamusService();
