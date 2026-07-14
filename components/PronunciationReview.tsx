import React, { useEffect, useRef, useState } from 'react';
import { gemini } from '../services/localService.ts';
import { Mic, Square, Play, Check, X, Trash2, Plus, Loader2, RefreshCw } from 'lucide-react';

type Item = {
  id: number; text: string; speaker_id: number | null; status: string;
  has_audio: boolean; note: string | null; updated_at: number;
};

const VOICES = [
  { v: '', label: 'Duk muryoyi (all)' },
  { v: '0', label: 'Malam Garba (M1)' }, { v: '4', label: 'Malama Asabe (F1)' },
  { v: '1', label: 'M2' }, { v: '2', label: 'M3' }, { v: '3', label: 'M4' },
  { v: '5', label: 'F2' }, { v: '6', label: 'F3' }, { v: '7', label: 'F4' },
];

/** Reusable mic recorder — calls onRecorded with a webm Blob. */
function useRecorder() {
  const [recording, setRecording] = useState(false);
  const mrRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const start = async (onDone: (b: Blob) => void) => {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      alert("Wannan browser ba ya goyon bayan yin rikodi ba. Gwada Chrome ko Safari na zamani. (This browser can't record audio.)");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      });
      // Pick a container this browser actually supports — Safari/iOS needs
      // audio/mp4, Chrome/Firefox use audio/webm. Forcing webm silently broke
      // recording on iOS. Fall back to the browser default if none report support.
      let mimeType = '';
      for (const t of ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/aac']) {
        if (MediaRecorder.isTypeSupported?.(t)) { mimeType = t; break; }
      }
      const mr = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
      mr.onstop = () => {
        onDone(new Blob(chunksRef.current, { type: mr.mimeType || 'audio/webm' }));
        stream.getTracks().forEach((t) => t.stop());
      };
      mr.start();
      mrRef.current = mr;
      setRecording(true);
    } catch (err: any) {
      const name = err?.name || '';
      if (name === 'NotAllowedError' || name === 'SecurityError')
        alert('An ƙi izinin makurufo. Ba da izini a saitunan browser sannan ka sāke gwadawa. (Microphone permission denied — allow it in your browser settings.)');
      else if (name === 'NotFoundError' || name === 'OverconstrainedError')
        alert('Ba a sami makurufo ba. (No microphone found on this device.)');
      else
        alert('Rikodi ya kāsa: ' + (name || 'error') + (err?.message ? ' — ' + err.message : ''));
    }
  };
  const stop = () => { mrRef.current?.stop(); setRecording(false); };
  return { recording, start, stop };
}

export const PronunciationReview: React.FC = () => {
  const [items, setItems] = useState<Item[]>([]);
  const [counts, setCounts] = useState<{ pending: number; approved: number; rejected: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [denied, setDenied] = useState(false);
  const [busy, setBusy] = useState<number | 'new' | null>(null);

  // New-correction form
  const [newText, setNewText] = useState('');
  const [newVoice, setNewVoice] = useState('');
  const [newBlob, setNewBlob] = useState<Blob | null>(null);
  const newRec = useRecorder();

  // Recording against an existing flag
  const [recForId, setRecForId] = useState<number | null>(null);
  const flagRec = useRecorder();

  const load = async () => {
    setLoading(true);
    const data = await gemini.getPronunciations();
    if (!data) { setDenied(true); setLoading(false); return; }
    setItems(data.items || []);
    setCounts(data.counts || null);
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const play = async (id: number) => {
    const url = await gemini.pronunciationAudioUrl(id);
    if (url) { const a = new Audio(url); a.play(); }
  };

  const submitNew = async () => {
    if (!newText.trim() || !newBlob) return;
    setBusy('new');
    const ok = await gemini.submitPronunciation(newText.trim(), newVoice ? Number(newVoice) : null, newBlob);
    setBusy(null);
    if (ok) { setNewText(''); setNewBlob(null); setNewVoice(''); load(); }
  };

  const recordForFlag = (id: number) => {
    setRecForId(id);
    flagRec.start(async (blob) => {
      setBusy(id);
      const ok = await gemini.recordPronunciation(id, blob);
      setBusy(null); setRecForId(null);
      if (ok) load();
    });
  };

  const setStatus = async (id: number, status: 'approved' | 'rejected') => {
    setBusy(id); await gemini.setPronunciationStatus(id, status); setBusy(null); load();
  };
  const remove = async (id: number) => {
    if (!confirm('Share wannan gyara? (delete)')) return;
    setBusy(id); await gemini.deletePronunciation(id); setBusy(null); load();
  };

  if (denied) return <p className="text-dyn-text-muted text-sm p-4">An hana shiga. Shiga a matsayin admin. (Admin login required.)</p>;

  const needsRecording = items.filter((i) => i.status === 'pending' && !i.has_audio);
  const awaitingApproval = items.filter((i) => i.status === 'pending' && i.has_audio);
  const approved = items.filter((i) => i.status === 'approved');

  return (
    <div className="space-y-8">
      {/* Header + counts */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h3 className="font-serif italic text-xl text-dyn-text-primary">Gyaran Furuci</h3>
          <p className="text-[10px] uppercase tracking-widest text-dyn-text-muted">Pronunciation corrections · human-in-the-loop</p>
        </div>
        <div className="flex items-center gap-4 text-xs">
          {counts && <>
            <span className="text-amber-400">{counts.pending} pending</span>
            <span className="text-emerald-400">{counts.approved} approved</span>
          </>}
          <button onClick={load} className="p-2 rounded-lg text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5" aria-label="Refresh"><RefreshCw className="w-4 h-4" /></button>
        </div>
      </div>

      {/* New correction recorder */}
      <div className="rounded-2xl border border-dyn-border bg-dyn-bg-tertiary/30 p-5 space-y-3">
        <label className="text-[10px] uppercase tracking-widest text-dyn-text-muted font-bold flex items-center gap-2"><Plus className="w-3.5 h-3.5 text-dyn-accent" /> Sabon gyara (record a correction)</label>
        <input value={newText} onChange={(e) => setNewText(e.target.value)} placeholder="Kalma ko jimla… (word or phrase to fix)"
          className="w-full rounded-xl bg-dyn-bg-tertiary/50 border border-dyn-border px-4 py-2.5 text-sm text-dyn-text-primary focus:outline-none focus:border-dyn-accent/50" />
        <div className="flex items-center gap-3 flex-wrap">
          <select value={newVoice} onChange={(e) => setNewVoice(e.target.value)} className="rounded-xl bg-dyn-bg-tertiary/50 border border-dyn-border px-3 py-2 text-xs text-dyn-text-primary focus:outline-none">
            {VOICES.map((v) => <option key={v.v} value={v.v}>{v.label}</option>)}
          </select>
          {!newRec.recording ? (
            <button onClick={() => newRec.start(setNewBlob)} disabled={!newText.trim()} className="flex items-center gap-2 px-4 py-2 rounded-xl border border-dyn-accent/50 text-dyn-accent text-xs font-bold uppercase tracking-wider hover:bg-dyn-accent/10 disabled:opacity-30">
              <Mic className="w-3.5 h-3.5" /> Yi rikodi (record)
            </button>
          ) : (
            <button onClick={newRec.stop} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-500/20 border border-red-500/50 text-red-400 text-xs font-bold uppercase tracking-wider animate-pulse">
              <Square className="w-3.5 h-3.5" /> Tsaya (stop)
            </button>
          )}
          {newBlob && !newRec.recording && (
            <>
              <button onClick={() => { const a = new Audio(URL.createObjectURL(newBlob)); a.play(); }} className="p-2 rounded-lg text-dyn-text-secondary hover:text-dyn-text-primary" aria-label="Preview"><Play className="w-4 h-4" /></button>
              <button onClick={submitNew} disabled={busy === 'new'} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/20 border border-emerald-500/50 text-emerald-400 text-xs font-bold uppercase tracking-wider hover:bg-emerald-500/30 disabled:opacity-40">
                {busy === 'new' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />} Ajiye (save)
              </button>
            </>
          )}
        </div>
      </div>

      {/* Flags that still need a recording */}
      {needsRecording.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] uppercase tracking-widest text-amber-400/80 font-bold">Waɗanda ake jira · flagged, need a recording ({needsRecording.length})</p>
          {needsRecording.map((it) => (
            <div key={it.id} className="flex items-center justify-between gap-3 rounded-xl border border-dyn-border bg-dyn-bg-tertiary/20 px-4 py-3">
              <div className="min-w-0">
                <p className="text-sm text-dyn-text-primary truncate">{it.text}</p>
                {it.note && <p className="text-[11px] text-dyn-text-muted truncate">“{it.note}”</p>}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {recForId === it.id && flagRec.recording ? (
                  <button onClick={flagRec.stop} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/20 border border-red-500/50 text-red-400 text-[11px] font-bold uppercase animate-pulse"><Square className="w-3 h-3" /> Stop</button>
                ) : (
                  <button onClick={() => recordForFlag(it.id)} disabled={busy === it.id} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-dyn-accent/50 text-dyn-accent text-[11px] font-bold uppercase hover:bg-dyn-accent/10 disabled:opacity-30">
                    {busy === it.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Mic className="w-3 h-3" />} Record
                  </button>
                )}
                <button onClick={() => remove(it.id)} className="p-1.5 rounded-lg text-dyn-text-muted hover:text-red-400" aria-label="Delete"><Trash2 className="w-3.5 h-3.5" /></button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Recorded — awaiting YOUR approval (nothing goes live without this) */}
      {awaitingApproval.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] uppercase tracking-widest text-amber-400/80 font-bold">Ana jira amincewarka · awaiting your approval ({awaitingApproval.length})</p>
          {awaitingApproval.map((it) => (
            <div key={it.id} className="flex items-center justify-between gap-3 rounded-xl border border-amber-500/30 bg-amber-500/[0.05] px-4 py-3">
              <div className="flex items-center gap-3 min-w-0">
                <button onClick={() => play(it.id)} className="p-2 rounded-lg bg-dyn-bg-tertiary/50 text-dyn-accent hover:bg-dyn-bg-tertiary shrink-0" aria-label="Listen before approving"><Play className="w-4 h-4" /></button>
                <div className="min-w-0">
                  <p className="text-sm text-dyn-text-primary truncate">{it.text}</p>
                  <p className="text-[10px] text-dyn-text-muted">{it.speaker_id === null ? 'duk muryoyi' : `voice ${it.speaker_id}`} · listen, then approve</p>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button onClick={() => setStatus(it.id, 'approved')} disabled={busy === it.id} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/20 border border-emerald-500/50 text-emerald-400 text-[11px] font-bold uppercase hover:bg-emerald-500/30 disabled:opacity-40">
                  {busy === it.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />} Amince (approve)
                </button>
                <button onClick={() => remove(it.id)} className="p-1.5 rounded-lg text-dyn-text-muted hover:text-red-400" aria-label="Reject & delete"><Trash2 className="w-3.5 h-3.5" /></button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Approved corrections — active overrides */}
      <div className="space-y-2">
        <p className="text-[10px] uppercase tracking-widest text-emerald-400/80 font-bold">Ana amfani da su · active overrides ({approved.length})</p>
        {approved.length === 0 && <p className="text-xs text-dyn-text-muted/50 italic py-2">Babu tukuna. (None yet — record one above.)</p>}
        {approved.map((it) => (
          <div key={it.id} className="flex items-center justify-between gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] px-4 py-3">
            <div className="flex items-center gap-3 min-w-0">
              <button onClick={() => play(it.id)} className="p-2 rounded-lg bg-dyn-bg-tertiary/50 text-dyn-accent hover:bg-dyn-bg-tertiary shrink-0" aria-label="Play"><Play className="w-4 h-4" /></button>
              <div className="min-w-0">
                <p className="text-sm text-dyn-text-primary truncate">{it.text}</p>
                <p className="text-[10px] text-dyn-text-muted">{it.speaker_id === null ? 'duk muryoyi' : `voice ${it.speaker_id}`}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button onClick={() => setStatus(it.id, 'rejected')} disabled={busy === it.id} className="p-1.5 rounded-lg text-dyn-text-muted hover:text-amber-400" aria-label="Disable"><X className="w-4 h-4" /></button>
              <button onClick={() => remove(it.id)} className="p-1.5 rounded-lg text-dyn-text-muted hover:text-red-400" aria-label="Delete"><Trash2 className="w-3.5 h-3.5" /></button>
            </div>
          </div>
        ))}
      </div>

      {loading && <div className="flex justify-center py-4"><Loader2 className="w-5 h-5 animate-spin text-dyn-accent" /></div>}
    </div>
  );
};
