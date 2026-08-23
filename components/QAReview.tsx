import React, { useEffect, useState } from 'react';
import { gemini } from '../services/localService.ts';
import { ConfirmDialog } from './ConfirmDialog.tsx';
import { Check, X, Trash2, Loader2, RefreshCw, Download } from 'lucide-react';

type Item = {
  id: number; question: string; answer: string; topic: string | null;
  status: string; submitted_by: string | null; updated_at: number;
};

/** Admin review of community Hausa Q&A — approve/reject native-written pairs and
 * export the approved set as instruction data for the LLM training mix. */
export const QAReview: React.FC = () => {
  const [items, setItems] = useState<Item[]>([]);
  const [counts, setCounts] = useState<{ pending: number; approved: number; rejected: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [denied, setDenied] = useState(false);
  const [busy, setBusy] = useState<number | null>(null);
  const [exporting, setExporting] = useState(false);
  // Per-item error from a failed approve/reject/delete — a failed action
  // must never silently leave the item's state unclear (deep-scan #14).
  const [rowErrors, setRowErrors] = useState<Record<number, string>>({});
  const [pendingDelete, setPendingDelete] = useState<Item | null>(null);

  const load = async () => {
    setLoading(true);
    const data = await gemini.getQA();
    if (!data) { setDenied(true); setLoading(false); return; }
    setItems(data.items || []); setCounts(data.counts || null); setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const clearError = (id: number) => setRowErrors(prev => { const next = { ...prev }; delete next[id]; return next; });

  const setStatus = async (id: number, status: 'approved' | 'rejected') => {
    if (busy !== null) return; // an action is already in flight
    setBusy(id); clearError(id);
    const ok = await gemini.setQAStatus(id, status);
    setBusy(null);
    if (ok) load();
    else setRowErrors(prev => ({ ...prev, [id]: 'Ba a iya adanawa ba. Ka sāke gwadawa. (Save failed — try again.)' }));
  };

  const requestDelete = (it: Item) => { if (busy === null) setPendingDelete(it); };

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    const id = pendingDelete.id;
    setBusy(id); clearError(id);
    const ok = await gemini.deleteQA(id);
    setBusy(null);
    setPendingDelete(null);
    if (ok) load();
    else setRowErrors(prev => ({ ...prev, [id]: 'Sharewa ya kāsa. Ka sāke gwadawa. (Delete failed — try again.)' }));
  };

  if (denied) return <p className="text-dyn-text-muted text-sm p-4">An hana shiga. (Admin login required.)</p>;

  const pending = items.filter((i) => i.status === 'pending');
  const approved = items.filter((i) => i.status === 'approved');

  const Card: React.FC<{ it: Item; approvedRow?: boolean }> = ({ it, approvedRow }) => (
    <div className={`rounded-xl border px-4 py-3 space-y-2 ${approvedRow ? 'border-emerald-500/20 bg-emerald-500/[0.04]' : 'border-dyn-border bg-dyn-bg-tertiary/20'}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <p className="text-sm text-dyn-text-primary font-medium">{it.question}</p>
          <p className="text-[13px] text-dyn-text-secondary leading-relaxed whitespace-pre-wrap">{it.answer}</p>
          {it.topic && <span className="inline-block text-[9px] uppercase tracking-widest text-dyn-accent/70">{it.topic}</span>}
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {!approvedRow && (
            <button onClick={() => setStatus(it.id, 'approved')} disabled={busy !== null} className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-emerald-500/20 border border-emerald-500/50 text-emerald-400 text-[10px] font-bold uppercase hover:bg-emerald-500/30 disabled:opacity-40" title="Approve">
              {busy === it.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
            </button>
          )}
          {approvedRow && (
            <button onClick={() => setStatus(it.id, 'rejected')} disabled={busy !== null} className="p-1.5 rounded-lg text-dyn-text-muted hover:text-amber-400 disabled:opacity-40" title="Disable">
              {busy === it.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <X className="w-4 h-4" />}
            </button>
          )}
          <button onClick={() => requestDelete(it)} disabled={busy !== null} className="p-1.5 rounded-lg text-dyn-text-muted hover:text-red-400 disabled:opacity-40" title="Delete"><Trash2 className="w-3.5 h-3.5" /></button>
        </div>
      </div>
      {rowErrors[it.id] && (
        <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-1.5">{rowErrors[it.id]}</div>
      )}
    </div>
  );

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h3 className="font-serif italic text-xl text-dyn-text-primary">Tambaya &amp; Amsa</h3>
          <p className="text-[10px] uppercase tracking-widest text-dyn-text-muted">Community Q&amp;A · native-written LLM training data</p>
        </div>
        <div className="flex items-center gap-3 text-xs">
          {counts && <>
            <span className="text-amber-400">{counts.pending} pending</span>
            <span className="text-emerald-400">{counts.approved} approved</span>
          </>}
          {counts && counts.approved > 0 && (
            <button onClick={async () => { setExporting(true); const ok = await gemini.exportQA(); setExporting(false); if (!ok) alert('Fitarwa ya kāsa. (Export failed.)'); }} disabled={exporting}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-dyn-accent/40 text-dyn-accent text-[10px] font-bold uppercase tracking-wider hover:bg-dyn-accent/10 disabled:opacity-40" title="Download approved Q&A as instruction JSONL">
              {exporting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />} Fitar da Koyo
            </button>
          )}
          <button onClick={load} className="p-2 rounded-lg text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5" aria-label="Refresh"><RefreshCw className="w-4 h-4" /></button>
        </div>
      </div>

      {pending.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] uppercase tracking-widest text-amber-400/80 font-bold">Ana jira amincewarka · awaiting your approval ({pending.length})</p>
          {pending.map((it) => <Card key={it.id} it={it} />)}
        </div>
      )}

      <div className="space-y-2">
        <p className="text-[10px] uppercase tracking-widest text-emerald-400/80 font-bold">Ana amfani da su a horo · in the training set ({approved.length})</p>
        {approved.length === 0 && <p className="text-xs text-dyn-text-muted/50 italic py-2">Babu tukuna. (None approved yet.)</p>}
        {approved.map((it) => <Card key={it.id} it={it} approvedRow />)}
      </div>

      {loading && <div className="flex justify-center py-4"><Loader2 className="w-5 h-5 animate-spin text-dyn-accent" /></div>}

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Share wannan Tambaya & Amsa?"
        message={pendingDelete ? `"${pendingDelete.question}" za a share shi har abada. Ba za a iya mayar da shi ba. (This Q&A pair will be permanently deleted. This cannot be undone.)` : ''}
        confirmLabel="Share (Delete)"
        busy={busy === pendingDelete?.id}
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
};
