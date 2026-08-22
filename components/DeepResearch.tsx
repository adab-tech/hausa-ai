import React, { useEffect, useRef, useState } from 'react';
import { gemini } from '../services/localService.ts';
import { Search, X, Loader2, Sparkles } from 'lucide-react';

type Phase = 'idle' | 'starting' | 'polling' | 'done' | 'error';

const POLL_INTERVAL_MS = 4000;
const MAX_POLLS = 45; // ~3 minutes — Tavily research tasks are typically done well before this

/** Deep, multi-step, cited research (Tavily Research) — an opt-in alternative
 * to the quick single-shot search grounding already built into ordinary chat.
 * Genuinely slower (10s to a few minutes) and costs more Tavily credits per
 * call, so this is a deliberate action, not something triggered automatically. */
export const DeepResearch: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const [query, setQuery] = useState('');
  const [phase, setPhase] = useState<Phase>('idle');
  const [report, setReport] = useState('');
  const [error, setError] = useState('');
  const pollCountRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [onClose]);

  const poll = async (requestId: string) => {
    if (pollCountRef.current >= MAX_POLLS) {
      setPhase('error');
      setError('Bincike ya ɗauki lokaci mai tsawo. Gwada sake yin tambaya mafi taƙaice. (Research is taking too long — try a more specific question.)');
      return;
    }
    pollCountRef.current += 1;
    const status = await gemini.getResearchStatus(requestId);
    if (!status) {
      setPhase('error');
      setError('An rasa alaƙa da binciken. (Lost track of the research task.)');
      return;
    }
    if (status.status === 'completed') {
      setReport(status.content || status.answer || status.report || '');
      setPhase('done');
      return;
    }
    if (status.status === 'failed') {
      setPhase('error');
      setError('Binciken ya kasa. Gwada wata tambaya. (The research task failed — try a different question.)');
      return;
    }
    timerRef.current = setTimeout(() => poll(requestId), POLL_INTERVAL_MS);
  };

  const start = async () => {
    if (query.trim().length < 3) return;
    setPhase('starting');
    setError('');
    setReport('');
    pollCountRef.current = 0;
    const requestId = await gemini.startResearch(query.trim());
    if (!requestId) {
      setPhase('error');
      setError('Ba a iya fara bincike ba. (Could not start research — the service may be unavailable.)');
      return;
    }
    setPhase('polling');
    timerRef.current = setTimeout(() => poll(requestId), POLL_INTERVAL_MS);
  };

  const busy = phase === 'starting' || phase === 'polling';

  return (
    <div className="fixed inset-0 z-[60] bg-dyn-bg-primary/95 backdrop-blur-xl flex flex-col animate-reveal">
      <header className="flex items-center justify-between px-6 sm:px-10 py-5 border-b border-dyn-border/40 shrink-0">
        <div className="flex items-center gap-3">
          <Search className="w-5 h-5 text-dyn-accent" />
          <div>
            <h2 className="font-serif italic text-xl text-dyn-text-primary leading-none">Zurfin Bincike</h2>
            <p className="text-[9px] uppercase tracking-[0.3em] text-dyn-text-muted mt-1">Deep, cited research</p>
          </div>
        </div>
        <button onClick={onClose} aria-label="Rufe (Close)" className="p-3 rounded-xl text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5"><X className="w-5 h-5" /></button>
      </header>

      <div className="flex-1 overflow-y-auto no-scrollbar p-6 sm:p-10 max-w-2xl w-full mx-auto space-y-6">
        <p className="text-sm text-dyn-text-secondary leading-relaxed">Yi tambaya mai zurfi — Murya za ta bincika hanyoyi da yawa a yanar gizo sannan ta tsara amsa cikakkiya, tare da tushen bayanai. Wannan yana ɗaukar lokaci fiye da tattaunawa ta yau da kullum (daga daƙiƙa 10 zuwa mintuna kaɗan). (Ask a deep question — Murya researches multiple sources and synthesizes a full, cited answer. Slower than ordinary chat: 10 seconds to a few minutes.)</p>

        <div className="flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !busy) start(); }}
            disabled={busy}
            maxLength={500}
            placeholder="misali: Menene tarihin Daular Sokoto?"
            className="flex-1 rounded-xl bg-dyn-bg-tertiary/50 border border-dyn-border px-4 py-3 text-sm text-dyn-text-primary focus:outline-none focus:border-dyn-accent/50 disabled:opacity-50"
          />
          <button
            onClick={start}
            disabled={busy || query.trim().length < 3}
            className="flex items-center gap-2 px-5 py-3 rounded-xl bg-dyn-accent text-dyn-bg-primary text-sm font-bold uppercase tracking-wider disabled:opacity-30 disabled:cursor-not-allowed shrink-0"
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            Bincika
          </button>
        </div>

        {phase === 'starting' && (
          <p className="text-xs text-dyn-text-muted italic flex items-center gap-2"><Loader2 className="w-3.5 h-3.5 animate-spin" /> Fara bincike… (Starting research…)</p>
        )}
        {phase === 'polling' && (
          <p className="text-xs text-dyn-text-muted italic flex items-center gap-2"><Loader2 className="w-3.5 h-3.5 animate-spin" /> Ana bincike, jira kaɗan… (Researching — this can take a minute or two.)</p>
        )}
        {phase === 'error' && (
          <p className="text-xs text-red-400/80 italic">{error}</p>
        )}
        {phase === 'done' && report && (
          <div className="rounded-2xl bg-dyn-bg-tertiary/20 border border-dyn-border p-5 sm:p-6">
            <div className="prose prose-sm prose-invert max-w-none whitespace-pre-wrap text-sm text-dyn-text-primary leading-relaxed">
              {report}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
