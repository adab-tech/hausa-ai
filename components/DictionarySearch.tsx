import { offlineKamus } from '../services/offlineKamusService.ts';
import React, { useEffect, useRef, useState } from 'react';
import { gemini } from '../services/localService.ts';
import { BookOpen, X, Loader2, Search, ArrowRight } from 'lucide-react';

type DictResult = { headword: string; translation: string; context: string; direction: string; source: string };

/** Standalone search over the same lexicon chat's hidden "ma'anar kalmar X"
 * tool trigger already uses (Robinson 1914 + Wiktionary + Newman 1977,
 * ~30,700 entries) — the single biggest data investment this project has
 * made, previously invisible unless a chat message happened to phrase a
 * lookup exactly right. */
export const DictionarySearch: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<DictResult[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(true);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  // Same stale-response guard as DocumentTool.tsx's runId: without it, an
  // out-of-order network response (e.g. the query for "a" resolves AFTER
  // the query for "aboki" that was typed right after it) can overwrite
  // newer, correct results with older ones.
  const runId = useRef(0);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    inputRef.current?.focus();
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const term = query.trim();
    if (term.length < 1) { setResults(null); return; }
    debounceRef.current = setTimeout(async () => {
      const id = ++runId.current;
      setBusy(true);
      const res = await gemini.searchDictionary(term);
      if (id !== runId.current) return; // superseded by a newer query
      setReady(res.ready);
      setResults(res.results);
      setBusy(false);
    }, 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query]);

  return (
    <div className="fixed inset-0 z-[60] bg-dyn-bg-primary/95 backdrop-blur-xl flex flex-col animate-reveal">
      <header className="flex items-center justify-between px-6 sm:px-10 py-5 border-b border-dyn-border/40 shrink-0">
        <div className="flex items-center gap-3">
          <BookOpen className="w-5 h-5 text-dyn-accent" />
          <div>
            <h2 className="font-serif italic text-xl text-dyn-text-primary leading-none">Ƙamus</h2>
            <p className="text-[9px] uppercase tracking-[0.3em] text-dyn-text-muted mt-1">Dictionary — Robinson · Wiktionary · Newman</p>
          </div>
        </div>
        <button onClick={onClose} aria-label="Rufe (Close)" className="p-3 rounded-xl text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5"><X className="w-5 h-5" /></button>
      </header>

      <div className="flex-1 overflow-y-auto no-scrollbar p-6 sm:p-10 max-w-2xl w-full mx-auto">
        <div className="relative mb-6">
          <Search className="w-4 h-4 text-dyn-text-muted absolute left-4 top-1/2 -translate-y-1/2" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            maxLength={100}
            placeholder="misali: ruwa, aboki, water, friend…"
            className="w-full rounded-xl bg-dyn-bg-tertiary/50 border border-dyn-border pl-11 pr-4 py-3.5 text-sm text-dyn-text-primary focus:outline-none focus:border-dyn-accent/50"
          />
          {busy && <Loader2 className="w-4 h-4 text-dyn-accent animate-spin absolute right-4 top-1/2 -translate-y-1/2" />}
        </div>

        {!ready && (
          <p className="text-sm text-dyn-text-muted text-center py-8">Ƙamus ba ya samuwa a yanzu. Gwada daga baya. (Dictionary unavailable right now — try again later.)</p>
        )}

        {ready && results !== null && results.length === 0 && !busy && (
          <p className="text-sm text-dyn-text-muted text-center py-8">Ba a sami "{query.trim()}" ba. (No results for "{query.trim()}".)</p>
        )}

        {ready && results === null && (
          <p className="text-sm text-dyn-text-muted/70 text-center py-8 italic">Rubuta kalma a Hausa ko Turanci don farawa. (Type a word in Hausa or English to start.)</p>
        )}

        {results && results.length > 0 && (
          <ul className="space-y-2.5">
            {results.map((r, i) => (
              <li key={i} className="rounded-xl bg-dyn-bg-tertiary/40 border border-dyn-border px-5 py-4">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <span className="font-serif italic text-lg text-dyn-accent">{r.headword}</span>
                  <ArrowRight className="w-3.5 h-3.5 text-dyn-text-muted shrink-0" />
                  <span className="text-sm text-dyn-text-primary">{r.translation}</span>
                </div>
                <div className="flex items-center gap-2 mt-2 text-[9px] uppercase tracking-wider text-dyn-text-muted">
                  {r.context && <span>{r.context}</span>}
                  {r.context && <span className="opacity-40">·</span>}
                  <span className="text-dyn-accent/70 font-bold">{r.source}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};
