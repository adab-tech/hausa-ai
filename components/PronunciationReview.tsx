import React, { useEffect, useRef, useState } from 'react';
import { gemini } from '../services/localService.ts';
import { ConfirmDialog } from './ConfirmDialog.tsx';
import { WavRecorder } from '../utils/wavRecorder.ts';
import { Mic, Square, Play, Check, X, Trash2, Plus, Loader2, RefreshCw, Download } from 'lucide-react';

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

/** Reusable mic recorder (WAV output; works on iOS/Safari) — calls onDone with
 * a WAV Blob when stopped. */
function useRecorder() {
  const [recording, setRecording] = useState(false);
  const recRef = useRef<WavRecorder | null>(null);
  const onDoneRef = useRef<((b: Blob) => void) | null>(null);

  const start = async (onDone: (b: Blob) => void) => {
    try {
      const rec = new WavRecorder();
      await rec.start();
      recRef.current = rec;
      onDoneRef.current = onDone;
      setRecording(true);
    } catch (err: any) {
      const name = err?.name || '';
      if (name === 'NotAllowedError' || name === 'SecurityError')
        alert('An ƙi izinin makurufo. Ba da izini a saitunan browser sannan ka sāke gwadawa. (Microphone permission denied — allow it in your browser settings.)');
      else if (name === 'NotFoundError' || name === 'OverconstrainedError')
        alert('Ba a sami makurufo ba. (No microphone found on this device.)');
      else if (name === 'NotSupportedError')
        alert("Wannan browser ba ya goyon bayan yin rikodi ba. (This browser can't record audio.)");
      else
        alert('Rikodi ya kāsa: ' + (name || 'error') + (err?.message ? ' — ' + err.message : ''));
    }
  };
  const stop = () => {
    try { const wav = recRef.current?.stop(); if (wav) onDoneRef.current?.(wav); } catch { /* ignore */ }
    recRef.current = null;
    setRecording(false);
  };

  // If the owning component unmounts mid-recording (e.g. the item this
  // recorder belongs to disappears from the list because another action
  // changed its status), release the mic instead of leaking the stream —
  // same class of bug as deep-scan finding #8 (live-voice hangup), just
  // scoped to this admin recorder.
  useEffect(() => {
    return () => {
      if (recRef.current) {
        try { recRef.current.stop(); } catch { /* ignore */ }
        recRef.current = null;
      }
    };
  }, []);

  return { recording, start, stop };
}

/**
 * One row's flag-recording UI, with its OWN useRecorder() instance. Before
 * this, every row in the "needs recording" list shared a single `flagRec`
 * object owned by the parent: starting a second row's recording called
 * flagRec.start() again, which created a brand-new WavRecorder and
 * overwrote the ref holding the FIRST row's still-live WavRecorder —
 * silently abandoning its open MediaStream (mic never released) instead of
 * stopping it (deep-scan #14). Giving each row its own hook instance means
 * each row's recorder lives in its own closure; there is no shared ref to
 * clobber, and useRecorder's unmount cleanup (above) releases the mic if
 * the row disappears mid-recording.
 */
const FlagRow: React.FC<{
  it: Item;
  busy: boolean;
  otherRowRecording: boolean;
  onRecordingChange: (id: number, recording: boolean) => void;
  onRecorded: (id: number, blob: Blob) => void;
  onDelete: (it: Item) => void;
}> = ({ it, busy, otherRowRecording, onRecordingChange, onRecorded, onDelete }) => {
  const rec = useRecorder();

  useEffect(() => { onRecordingChange(it.id, rec.recording); }, [rec.recording, it.id, onRecordingChange]);

  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-dyn-border bg-dyn-bg-tertiary/20 px-4 py-3">
      <div className="min-w-0">
        <p className="text-sm text-dyn-text-primary truncate">{it.text}</p>
        {it.note && <p className="text-[11px] text-dyn-text-muted truncate">“{it.note}”</p>}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {rec.recording ? (
          <button onClick={rec.stop} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/20 border border-red-500/50 text-red-400 text-[11px] font-bold uppercase animate-pulse"><Square className="w-3 h-3" /> Stop</button>
        ) : (
          <button
            onClick={() => rec.start((blob) => onRecorded(it.id, blob))}
            disabled={busy || otherRowRecording}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-dyn-accent/50 text-dyn-accent text-[11px] font-bold uppercase hover:bg-dyn-accent/10 disabled:opacity-30"
          >
            {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <Mic className="w-3 h-3" />} Record
          </button>
        )}
        <button onClick={() => onDelete(it)} disabled={busy || rec.recording} className="p-1.5 rounded-lg text-dyn-text-muted hover:text-red-400 disabled:opacity-30" aria-label="Delete"><Trash2 className="w-3.5 h-3.5" /></button>
      </div>
    </div>
  );
};

export const PronunciationReview: React.FC = () => {
  const [items, setItems] = useState<Item[]>([]);
  const [counts, setCounts] = useState<{ pending: number; approved: number; rejected: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [denied, setDenied] = useState(false);
  const [busy, setBusy] = useState<number | 'new' | null>(null);
  const [exporting, setExporting] = useState(false);
  // Per-item error from a failed approve/reject/record/delete — a failed
  // action must never silently leave the item's state unclear (deep-scan #14).
  const [rowErrors, setRowErrors] = useState<Record<number, string>>({});
  const [pendingDelete, setPendingDelete] = useState<Item | null>(null);
  // Which flagged row (if any) currently has a live mic recording, so other
  // rows' Record buttons can be disabled while it's active — a UX guard on
  // top of the real fix (each row now owns its own recorder, see FlagRow).
  const [recordingRowId, setRecordingRowId] = useState<number | null>(null);

  // New-correction form
  const [newText, setNewText] = useState('');
  const [newVoice, setNewVoice] = useState('');
  const [newBlob, setNewBlob] = useState<Blob | null>(null);
  const newRec = useRecorder();

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

  const clearError = (id: number) => setRowErrors(prev => { const next = { ...prev }; delete next[id]; return next; });

  const submitNew = async () => {
    if (!newText.trim() || !newBlob) return;
    setBusy('new');
    const ok = await gemini.submitPronunciation(newText.trim(), newVoice ? Number(newVoice) : null, newBlob);
    setBusy(null);
    if (ok) { setNewText(''); setNewBlob(null); setNewVoice(''); load(); }
    else alert('Ajiyewa ya kāsa. Ka sāke gwadawa. (Save failed — try again.)');
  };

  const recordForFlag = async (id: number, blob: Blob) => {
    if (busy !== null) return; // an action is already in flight
    setBusy(id); clearError(id);
    const ok = await gemini.recordPronunciation(id, blob);
    setBusy(null);
    if (ok) load();
    else setRowErrors(prev => ({ ...prev, [id]: 'Ajiyewa ya kāsa. Ka sāke gwadawa. (Save failed — try again.)' }));
  };

  const setStatus = async (id: number, status: 'approved' | 'rejected') => {
    if (busy !== null) return;
    setBusy(id); clearError(id);
    const ok = await gemini.setPronunciationStatus(id, status);
    setBusy(null);
    if (ok) load();
    else setRowErrors(prev => ({ ...prev, [id]: 'Ba a iya adanawa ba. Ka sāke gwadawa. (Save failed — try again.)' }));
  };

  const requestDelete = (it: Item) => { if (busy === null) setPendingDelete(it); };

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    const id = pendingDelete.id;
    setBusy(id); clearError(id);
    const ok = await gemini.deletePronunciation(id);
    setBusy(null);
    setPendingDelete(null);
    if (ok) load();
    else setRowErrors(prev => ({ ...prev, [id]: 'Sharewa ya kāsa. Ka sāke gwadawa. (Delete failed — try again.)' }));
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
        <div className="flex items-center gap-3 text-xs">
          {counts && <>
            <span className="text-amber-400">{counts.pending} pending</span>
            <span className="text-emerald-400">{counts.approved} approved</span>
          </>}
          {counts && counts.approved > 0 && (
            <button
              onClick={async () => { setExporting(true); const ok = await gemini.exportPronunciationCorpus(); setExporting(false); if (!ok) alert('Fitarwa ya kāsa. (Export failed.)'); }}
              disabled={exporting}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-dyn-accent/40 text-dyn-accent text-[10px] font-bold uppercase tracking-wider hover:bg-dyn-accent/10 disabled:opacity-40"
              title="Download approved corrections as a training corpus (ZIP)"
            >
              {exporting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />} Fitar da Koyo
            </button>
          )}
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

      {/* Flags that still need a recording — each row owns its own recorder
          instance (FlagRow) so starting one row's recording can never
          abandon another row's live mic stream. */}
      {needsRecording.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] uppercase tracking-widest text-amber-400/80 font-bold">Waɗanda ake jira · flagged, need a recording ({needsRecording.length})</p>
          {needsRecording.map((it) => (
            <div key={it.id} className="space-y-1">
              <FlagRow
                it={it}
                busy={busy === it.id}
                otherRowRecording={recordingRowId !== null && recordingRowId !== it.id}
                onRecordingChange={(id, recording) => setRecordingRowId(prev => (recording ? id : (prev === id ? null : prev)))}
                onRecorded={recordForFlag}
                onDelete={requestDelete}
              />
              {rowErrors[it.id] && (
                <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-1.5">{rowErrors[it.id]}</div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Recorded — awaiting YOUR approval (nothing goes live without this) */}
      {awaitingApproval.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] uppercase tracking-widest text-amber-400/80 font-bold">Ana jira amincewarka · awaiting your approval ({awaitingApproval.length})</p>
          {awaitingApproval.map((it) => (
            <div key={it.id} className="space-y-1">
              <div className="flex items-center justify-between gap-3 rounded-xl border border-amber-500/30 bg-amber-500/[0.05] px-4 py-3">
                <div className="flex items-center gap-3 min-w-0">
                  <button onClick={() => play(it.id)} className="p-2 rounded-lg bg-dyn-bg-tertiary/50 text-dyn-accent hover:bg-dyn-bg-tertiary shrink-0" aria-label="Listen before approving"><Play className="w-4 h-4" /></button>
                  <div className="min-w-0">
                    <p className="text-sm text-dyn-text-primary truncate">{it.text}</p>
                    <p className="text-[10px] text-dyn-text-muted">{it.speaker_id === null ? 'duk muryoyi' : `voice ${it.speaker_id}`} · listen, then approve</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button onClick={() => setStatus(it.id, 'approved')} disabled={busy !== null} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/20 border border-emerald-500/50 text-emerald-400 text-[11px] font-bold uppercase hover:bg-emerald-500/30 disabled:opacity-40">
                    {busy === it.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />} Amince (approve)
                  </button>
                  <button onClick={() => requestDelete(it)} disabled={busy !== null} className="p-1.5 rounded-lg text-dyn-text-muted hover:text-red-400 disabled:opacity-40" aria-label="Reject & delete"><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              </div>
              {rowErrors[it.id] && (
                <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-1.5">{rowErrors[it.id]}</div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Approved corrections — active overrides */}
      <div className="space-y-2">
        <p className="text-[10px] uppercase tracking-widest text-emerald-400/80 font-bold">Ana amfani da su · active overrides ({approved.length})</p>
        {approved.length === 0 && <p className="text-xs text-dyn-text-muted/50 italic py-2">Babu tukuna. (None yet — record one above.)</p>}
        {approved.map((it) => (
          <div key={it.id} className="space-y-1">
            <div className="flex items-center justify-between gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] px-4 py-3">
              <div className="flex items-center gap-3 min-w-0">
                <button onClick={() => play(it.id)} className="p-2 rounded-lg bg-dyn-bg-tertiary/50 text-dyn-accent hover:bg-dyn-bg-tertiary shrink-0" aria-label="Play"><Play className="w-4 h-4" /></button>
                <div className="min-w-0">
                  <p className="text-sm text-dyn-text-primary truncate">{it.text}</p>
                  <p className="text-[10px] text-dyn-text-muted">{it.speaker_id === null ? 'duk muryoyi' : `voice ${it.speaker_id}`}</p>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button onClick={() => setStatus(it.id, 'rejected')} disabled={busy !== null} className="p-1.5 rounded-lg text-dyn-text-muted hover:text-amber-400 disabled:opacity-40" aria-label="Disable">
                  {busy === it.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <X className="w-4 h-4" />}
                </button>
                <button onClick={() => requestDelete(it)} disabled={busy !== null} className="p-1.5 rounded-lg text-dyn-text-muted hover:text-red-400 disabled:opacity-40" aria-label="Delete"><Trash2 className="w-3.5 h-3.5" /></button>
              </div>
            </div>
            {rowErrors[it.id] && (
              <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-1.5">{rowErrors[it.id]}</div>
            )}
          </div>
        ))}
      </div>

      {loading && <div className="flex justify-center py-4"><Loader2 className="w-5 h-5 animate-spin text-dyn-accent" /></div>}

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Share wannan gyara?"
        message={pendingDelete ? `"${pendingDelete.text}" — za a share wannan gyaran furuci har abada. Ba za a iya mayar da shi ba. (This pronunciation correction will be permanently deleted. This cannot be undone.)` : ''}
        confirmLabel="Share (Delete)"
        busy={busy === pendingDelete?.id}
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
};
