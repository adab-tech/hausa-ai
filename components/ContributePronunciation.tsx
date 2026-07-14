import React, { useEffect, useRef, useState } from 'react';
import { gemini } from '../services/localService.ts';
import { WavRecorder } from '../utils/wavRecorder.ts';
import { Mic, Square, Play, X, Check, Loader2, Send } from 'lucide-react';

const VOICES = [
  { v: '', label: 'Duk muryoyi (any voice)' },
  { v: '0', label: 'Malam Garba (namiji)' },
  { v: '4', label: 'Malama Asabe (mace)' },
];

/** User-facing: contribute the correct pronunciation of a Hausa word/phrase.
 * Records audio (works on iOS/Safari) + optional note; submits as PENDING for
 * the owner to review and approve. Nothing goes live without that approval. */
export const ContributePronunciation: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const [text, setText] = useState('');
  const [note, setNote] = useState('');
  const [voice, setVoice] = useState('');
  const [blob, setBlob] = useState<Blob | null>(null);
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const recRef = useRef<WavRecorder | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const startRec = async () => {
    try {
      const rec = new WavRecorder();
      await rec.start();
      recRef.current = rec;
      setBlob(null);
      setRecording(true);
    } catch (err: any) {
      const name = err?.name || '';
      if (name === 'NotAllowedError' || name === 'SecurityError') alert('An ƙi izinin makurufo. Ba da izini a saitunan browser. (Microphone permission denied — allow it in browser settings.)');
      else if (name === 'NotFoundError' || name === 'OverconstrainedError') alert('Ba a sami makurufo ba. (No microphone found.)');
      else if (name === 'NotSupportedError') alert("Wannan browser ba ya goyon bayan yin rikodi ba. (This browser can't record audio.)");
      else alert('Rikodi ya kāsa: ' + (name || 'error') + (err?.message ? ' — ' + err.message : ''));
    }
  };
  const stopRec = () => {
    try { const wav = recRef.current?.stop(); if (wav) setBlob(wav); } catch { /* ignore */ }
    recRef.current = null;
    setRecording(false);
  };

  const submit = async () => {
    if (!text.trim() || !blob) return;
    setBusy(true);
    const ok = await gemini.submitUserPronunciation(text.trim(), voice ? Number(voice) : null, blob, note.trim() || undefined);
    setBusy(false);
    if (ok) setDone(true);
  };

  return (
    <div className="fixed inset-0 z-[60] bg-dyn-bg-primary/95 backdrop-blur-xl flex flex-col animate-reveal">
      <header className="flex items-center justify-between px-6 sm:px-10 py-5 border-b border-dyn-border/40 shrink-0">
        <div className="flex items-center gap-3">
          <Mic className="w-5 h-5 text-dyn-accent" />
          <div>
            <h2 className="font-serif italic text-xl text-dyn-text-primary leading-none">Gyara Furuci</h2>
            <p className="text-[9px] uppercase tracking-[0.3em] text-dyn-text-muted mt-1">Contribute a pronunciation</p>
          </div>
        </div>
        <button onClick={onClose} aria-label="Rufe (Close)" className="p-3 rounded-xl text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5"><X className="w-5 h-5" /></button>
      </header>

      <div className="flex-1 overflow-y-auto no-scrollbar p-6 sm:p-10 max-w-xl w-full mx-auto">
        {done ? (
          <div className="text-center py-16 space-y-4">
            <div className="w-14 h-14 rounded-full bg-emerald-500/20 border border-emerald-500/50 flex items-center justify-center mx-auto"><Check className="w-7 h-7 text-emerald-400" /></div>
            <h3 className="font-serif italic text-2xl text-dyn-text-primary">Na gode! (Thank you)</h3>
            <p className="text-sm text-dyn-text-secondary max-w-sm mx-auto">An aika gyaranka. Mai kula zai duba shi kafin a yi amfani da shi. (Your correction was sent — the owner will review it before it's used.)</p>
            <button onClick={onClose} className="mt-4 px-6 py-2.5 rounded-full bg-dyn-accent text-dyn-bg-primary text-xs font-bold uppercase tracking-wider">Rufe (Close)</button>
          </div>
        ) : (
          <div className="space-y-6">
            <p className="text-sm text-dyn-text-secondary leading-relaxed">Idan Murya ta furta wata kalma ba daidai ba, ka rubuta ta sannan ka yi rikodin yadda ya kamata a faɗe ta. (If Murya says a word wrong, type it and record how it should sound.)</p>

            <div className="space-y-2">
              <label className="text-[10px] uppercase tracking-widest text-dyn-text-muted font-bold">Kalma / Jimla (Word or phrase)</label>
              <input value={text} onChange={(e) => setText(e.target.value)} maxLength={200} placeholder="misali: ƙoshin lafiya"
                className="w-full rounded-xl bg-dyn-bg-tertiary/50 border border-dyn-border px-4 py-3 text-sm text-dyn-text-primary focus:outline-none focus:border-dyn-accent/50" />
            </div>

            <div className="space-y-2">
              <label className="text-[10px] uppercase tracking-widest text-dyn-text-muted font-bold">Bayani (Note — optional)</label>
              <input value={note} onChange={(e) => setNote(e.target.value)} maxLength={300} placeholder="Ƙarin bayani… (any extra context)"
                className="w-full rounded-xl bg-dyn-bg-tertiary/50 border border-dyn-border px-4 py-3 text-sm text-dyn-text-primary focus:outline-none focus:border-dyn-accent/50" />
            </div>

            <div className="space-y-2">
              <label className="text-[10px] uppercase tracking-widest text-dyn-text-muted font-bold">Murya (Voice — optional)</label>
              <select value={voice} onChange={(e) => setVoice(e.target.value)} className="w-full rounded-xl bg-dyn-bg-tertiary/50 border border-dyn-border px-4 py-3 text-sm text-dyn-text-primary focus:outline-none">
                {VOICES.map((v) => <option key={v.v} value={v.v}>{v.label}</option>)}
              </select>
            </div>

            <div className="flex items-center gap-3 flex-wrap pt-2">
              {!recording ? (
                <button onClick={startRec} disabled={!text.trim()} className="flex items-center gap-2 px-5 py-3 rounded-xl border border-dyn-accent/50 text-dyn-accent text-xs font-bold uppercase tracking-wider hover:bg-dyn-accent/10 disabled:opacity-30">
                  <Mic className="w-4 h-4" /> Yi rikodi (record)
                </button>
              ) : (
                <button onClick={stopRec} className="flex items-center gap-2 px-5 py-3 rounded-xl bg-red-500/20 border border-red-500/50 text-red-400 text-xs font-bold uppercase tracking-wider animate-pulse">
                  <Square className="w-4 h-4" /> Tsaya (stop)
                </button>
              )}
              {blob && !recording && (
                <button onClick={() => { const a = new Audio(URL.createObjectURL(blob)); a.play(); }} className="flex items-center gap-2 px-4 py-3 rounded-xl border border-dyn-border text-dyn-text-secondary text-xs hover:text-dyn-text-primary">
                  <Play className="w-4 h-4" /> Saurara
                </button>
              )}
            </div>

            <button onClick={submit} disabled={!text.trim() || !blob || busy} className="w-full flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-dyn-accent text-dyn-bg-primary text-sm font-bold uppercase tracking-wider disabled:opacity-30 disabled:cursor-not-allowed">
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Aika gyara (Submit correction)
            </button>
            <p className="text-[11px] text-dyn-text-muted/70 text-center italic">Ba za a yi amfani da shi ba sai mai kula ya amince. (Not used until the owner approves.)</p>
          </div>
        )}
      </div>
    </div>
  );
};
