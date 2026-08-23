import React, { useEffect, useState } from 'react';
import { gemini } from '../services/localService.ts';
import { MessageSquarePlus, X, Check, Loader2, Send, AlertTriangle } from 'lucide-react';

/** User-facing: contribute a native-written Hausa question + answer. Feeds the
 * LLM training mix (Milestone #1) — submitted as PENDING, used only after the
 * owner approves. This is the highest-value data source for a native Hausa mind. */
export const ContributeQA: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [topic, setTopic] = useState('');
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const submit = async () => {
    if (question.trim().length < 2 || answer.trim().length < 2) return;
    setBusy(true);
    setError(null);
    const ok = await gemini.submitQA(question.trim(), answer.trim(), topic.trim() || undefined);
    setBusy(false);
    if (ok) setDone(true);
    else setError('An kasa aikawa. A sake gwadawa. (Failed to submit — please try again.)');
  };

  return (
    <div className="fixed inset-0 z-[60] bg-dyn-bg-primary/95 backdrop-blur-xl flex flex-col animate-reveal">
      <header className="flex items-center justify-between px-6 sm:px-10 py-5 border-b border-dyn-border/40 shrink-0">
        <div className="flex items-center gap-3">
          <MessageSquarePlus className="w-5 h-5 text-dyn-accent" />
          <div>
            <h2 className="font-serif italic text-xl text-dyn-text-primary leading-none">Ba da Tambaya da Amsa</h2>
            <p className="text-[9px] uppercase tracking-[0.3em] text-dyn-text-muted mt-1">Teach Murya real Hausa</p>
          </div>
        </div>
        <button onClick={onClose} aria-label="Rufe (Close)" className="p-3 rounded-xl text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5"><X className="w-5 h-5" /></button>
      </header>

      <div className="flex-1 overflow-y-auto no-scrollbar p-6 sm:p-10 max-w-xl w-full mx-auto">
        {done ? (
          <div className="text-center py-16 space-y-4">
            <div className="w-14 h-14 rounded-full bg-emerald-500/20 border border-emerald-500/50 flex items-center justify-center mx-auto"><Check className="w-7 h-7 text-emerald-400" /></div>
            <h3 className="font-serif italic text-2xl text-dyn-text-primary">Na gode! (Thank you)</h3>
            <p className="text-sm text-dyn-text-secondary max-w-sm mx-auto">Gudummawarka za ta taimaka wajen koya wa Murya Hausa ta gaskiya. Mai kula zai duba ta. (Your contribution helps teach Murya real Hausa — the owner will review it.)</p>
            <button onClick={onClose} className="mt-4 px-6 py-2.5 rounded-full bg-dyn-accent text-dyn-bg-primary text-xs font-bold uppercase tracking-wider">Rufe (Close)</button>
          </div>
        ) : (
          <div className="space-y-6">
            <p className="text-sm text-dyn-text-secondary leading-relaxed">Rubuta tambaya a Hausa, sannan ka rubuta amsar da ta dace — kamar yadda ƙwararren mai magana da Hausa zai amsa. Wannan yana koya wa Murya tunani da magana da Hausa ta gaskiya. (Write a Hausa question and the ideal Hausa answer — this teaches Murya to think and speak authentic Hausa.)</p>

            {error && (
              <div role="alert" className="flex items-start gap-3 p-4 rounded-2xl bg-red-500/[0.06] border border-red-500/30 animate-reveal">
                <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-red-400" />
                <p className="text-sm text-dyn-text-primary/90 leading-relaxed">{error}</p>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-[10px] uppercase tracking-widest text-dyn-text-muted font-bold">Tambaya (Question, in Hausa)</label>
              <textarea value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={1000} rows={2}
                placeholder="misali: Menene muhimmancin karatu a al'adar Hausa?"
                className="w-full resize-none rounded-xl bg-dyn-bg-tertiary/50 border border-dyn-border px-4 py-3 text-sm text-dyn-text-primary leading-relaxed focus:outline-none focus:border-dyn-accent/50 no-scrollbar" />
            </div>

            <div className="space-y-2">
              <label className="text-[10px] uppercase tracking-widest text-dyn-text-muted font-bold">Amsa (Answer, in Hausa)</label>
              <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} maxLength={4000} rows={5}
                placeholder="Rubuta amsa cikakkiya, mai dacewa da al'ada… (Write a full, culturally-grounded answer.)"
                className="w-full resize-none rounded-xl bg-dyn-bg-tertiary/50 border border-dyn-border px-4 py-3 text-sm text-dyn-text-primary leading-relaxed focus:outline-none focus:border-dyn-accent/50 no-scrollbar" />
            </div>

            <div className="space-y-2">
              <label className="text-[10px] uppercase tracking-widest text-dyn-text-muted font-bold">Fanni (Topic — optional)</label>
              <input value={topic} onChange={(e) => setTopic(e.target.value)} maxLength={80} placeholder="misali: tarihi, addini, al'ada, kimiyya"
                className="w-full rounded-xl bg-dyn-bg-tertiary/50 border border-dyn-border px-4 py-3 text-sm text-dyn-text-primary focus:outline-none focus:border-dyn-accent/50" />
            </div>

            <button onClick={submit} disabled={question.trim().length < 2 || answer.trim().length < 2 || busy} className="w-full flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-dyn-accent text-dyn-bg-primary text-sm font-bold uppercase tracking-wider disabled:opacity-30 disabled:cursor-not-allowed">
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Aika (Submit)
            </button>
            <p className="text-[11px] text-dyn-text-muted/70 text-center italic">Ba za a yi amfani da ita ba sai mai kula ya amince. (Not used until the owner approves.)</p>
          </div>
        )}
      </div>
    </div>
  );
};
