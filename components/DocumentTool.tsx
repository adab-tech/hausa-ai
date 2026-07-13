import React, { useState, useEffect, useRef } from 'react';
import { gemini } from '../services/localService.ts';
import { Languages, FileText, X, Copy, Check, Loader2, ArrowRight } from 'lucide-react';

type Action = 'translate' | 'summarize';
type Target = 'ha' | 'en';

const ACTIONS: { key: string; action: Action; target: Target; label: string; sub: string }[] = [
  { key: 't-en', action: 'translate', target: 'en', label: 'Zuwa Turanci', sub: 'Translate → English' },
  { key: 't-ha', action: 'translate', target: 'ha', label: 'Zuwa Hausa', sub: 'Translate → Hausa' },
  { key: 's-ha', action: 'summarize', target: 'ha', label: 'Takaita (Hausa)', sub: 'Summarize in Hausa' },
  { key: 's-en', action: 'summarize', target: 'en', label: 'Takaita (Turanci)', sub: 'Summarize in English' },
];

export const DocumentTool: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const [input, setInput] = useState('');
  const [result, setResult] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const runId = useRef(0);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const run = async (key: string, action: Action, target: Target) => {
    if (!input.trim() || busy) return;
    const id = ++runId.current;
    setBusy(key); setError(null); setResult('');
    for await (const chunk of gemini.streamDocument(input, action, target)) {
      if (id !== runId.current) return; // superseded
      if (chunk.error) { setError(chunk.error); break; }
      setResult(chunk.text);
    }
    if (id === runId.current) setBusy(null);
  };

  const copy = async () => {
    try { await navigator.clipboard.writeText(result); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { /* ignore */ }
  };

  return (
    <div className="fixed inset-0 z-[60] bg-dyn-bg-primary/95 backdrop-blur-xl flex flex-col animate-reveal">
      <header className="flex items-center justify-between px-6 sm:px-10 py-5 border-b border-dyn-border/40 shrink-0">
        <div className="flex items-center gap-3">
          <Languages className="w-5 h-5 text-dyn-accent" />
          <div>
            <h2 className="font-serif italic text-xl text-dyn-text-primary leading-none">Fassara &amp; Takaitawa</h2>
            <p className="text-[9px] uppercase tracking-[0.3em] text-dyn-text-muted mt-1">Translate &amp; Summarize</p>
          </div>
        </div>
        <button onClick={onClose} aria-label="Rufe (Close)" className="p-3 rounded-xl text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5">
          <X className="w-5 h-5" />
        </button>
      </header>

      <div className="flex-1 overflow-y-auto no-scrollbar p-6 sm:p-10 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input */}
        <div className="flex flex-col gap-3">
          <label className="text-[10px] uppercase tracking-widest text-dyn-text-muted font-bold flex items-center gap-2">
            <FileText className="w-3.5 h-3.5 text-dyn-accent" /> Rubutu (Your text — Hausa or English)
          </label>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            maxLength={30000}
            placeholder="Manna rubutunka anan… (Paste text here — up to ~30,000 characters)"
            className="flex-1 min-h-[220px] resize-none rounded-2xl bg-dyn-bg-tertiary/40 border border-dyn-border p-4 text-sm text-dyn-text-primary leading-relaxed focus:outline-none focus:border-dyn-accent/50 placeholder:text-dyn-text-muted/40 no-scrollbar"
          />
          <div className="flex justify-between items-center text-[9px] font-mono text-dyn-text-muted">
            <span>{input.length.toLocaleString()} / 30,000</span>
            {input && <button onClick={() => { setInput(''); setResult(''); setError(null); }} className="hover:text-dyn-text-secondary uppercase tracking-wider">Share (Clear)</button>}
          </div>
          <div className="grid grid-cols-2 gap-2">
            {ACTIONS.map((a) => (
              <button
                key={a.key}
                onClick={() => run(a.key, a.action, a.target)}
                disabled={!input.trim() || !!busy}
                className="min-h-[52px] px-3 py-2 rounded-xl border border-dyn-border bg-dyn-bg-tertiary/50 hover:border-dyn-accent/50 hover:bg-dyn-bg-tertiary text-left transition-all disabled:opacity-30 disabled:cursor-not-allowed group"
              >
                <span className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-dyn-text-primary">
                  {busy === a.key ? <Loader2 className="w-3.5 h-3.5 animate-spin text-dyn-accent" /> : <ArrowRight className="w-3.5 h-3.5 text-dyn-accent" />}
                  {a.label}
                </span>
                <span className="block text-[9px] text-dyn-text-muted mt-0.5">{a.sub}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Output */}
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <label className="text-[10px] uppercase tracking-widest text-dyn-text-muted font-bold">Sakamako (Result)</label>
            {result && !busy && (
              <button onClick={copy} className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-dyn-accent hover:text-dyn-accent/80 font-bold">
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? 'An kwafa' : 'Kwafa (Copy)'}
              </button>
            )}
          </div>
          <div className="flex-1 min-h-[220px] rounded-2xl bg-dyn-bg-tertiary/20 border border-dyn-border p-4 text-sm text-dyn-text-primary leading-relaxed whitespace-pre-wrap overflow-y-auto no-scrollbar">
            {error ? (
              <span className="text-red-400/80 italic">{error}</span>
            ) : result ? (
              <>{result}{busy && <span className="inline-block w-2 h-4 bg-dyn-accent/60 ml-0.5 animate-pulse align-middle" />}</>
            ) : (
              <span className="text-dyn-text-muted/40 italic">Sakamakon zai bayyana anan. (The result appears here.)</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
