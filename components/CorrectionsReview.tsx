import React, { useEffect, useState } from 'react';
import { gemini } from '../services/localService.ts';
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react';

interface Correction {
  id: string;
  messageId: string;
  originalText: string;
  correction: string;
  status: 'pending' | 'approved' | 'rejected';
  timestamp: number;
  reviewedBy?: string | null;
}

/**
 * Human-in-the-loop review queue. Only reachable from within AdminPanel,
 * which already confirmed a valid admin session (see admin_store.py) —
 * every request here rides that session cookie automatically.
 */
export const CorrectionsReview: React.FC = () => {
  const [pending, setPending] = useState<Correction[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Which row has an approve/reject request in flight — disables its buttons
  // and blocks a second click from firing a concurrent request for the same
  // row (see docs/deep_scan_2026-08-23.md finding #14).
  const [busyId, setBusyId] = useState<string | null>(null);
  // Per-row error from a failed approve/reject, so a failure is visible on
  // the item itself instead of leaving it silently stuck in "pending" with
  // no indication anything went wrong.
  const [rowErrors, setRowErrors] = useState<Record<string, string>>({});

  const loadPending = async () => {
    setError(null);
    const data = await gemini.getCorrections('pending');
    if (data === null) {
      setError('Ba a iya samun bayanai ba.');
      setPending(null);
    } else {
      setPending(data);
    }
  };

  useEffect(() => {
    loadPending();
  }, []);

  const review = async (id: string, action: 'approve' | 'reject') => {
    if (busyId) return; // a request for some row is already in flight
    setBusyId(id);
    setRowErrors(prev => { const next = { ...prev }; delete next[id]; return next; });
    const ok = await gemini.reviewCorrection(id, action);
    setBusyId(null);
    if (ok) {
      setPending(prev => (prev ? prev.filter(c => c.id !== id) : prev));
    } else {
      setRowErrors(prev => ({
        ...prev,
        [id]: action === 'approve'
          ? 'Amincewa ya kāsa. Ka sāke gwadawa. (Approve failed — try again.)'
          : 'Ƙin amincewa ya kāsa. Ka sāke gwadawa. (Reject failed — try again.)',
      }));
    }
  };

  return (
    <div className="space-y-6 animate-reveal">
      {error && (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={loadPending} className="text-xs underline">
            Sake gwadawa
          </button>
        </div>
      )}

      {pending && pending.length === 0 && !error && (
        <div className="text-center py-12 text-dyn-text-muted italic text-sm">
          Babu wani gyara da ke jiran bita. (No corrections pending review.)
        </div>
      )}

      {pending && pending.map((c) => (
        <div key={c.id} className="p-6 rounded-3xl bg-dyn-bg-tertiary/20 border border-dyn-border space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <span className="text-[9px] uppercase tracking-wider text-red-400/70 font-bold block mb-1">Original (flagged)</span>
              <p className="text-sm font-serif text-dyn-text-primary/90">{c.originalText || '(no text captured)'}</p>
            </div>
            <div>
              <span className="text-[9px] uppercase tracking-wider text-green-400/70 font-bold block mb-1">Proposed correction</span>
              <p className="text-sm font-serif text-dyn-text-primary">{c.correction}</p>
            </div>
          </div>
          {rowErrors[c.id] && (
            <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded-xl px-3 py-2">
              {rowErrors[c.id]}
            </div>
          )}
          <div className="flex items-center justify-between pt-3 border-t border-dyn-border/30">
            <span className="text-[9px] font-mono text-dyn-text-muted">{new Date(c.timestamp * 1000).toLocaleString()}</span>
            <div className="flex gap-3">
              <button
                onClick={() => review(c.id, 'reject')}
                disabled={busyId === c.id}
                className="flex items-center gap-1.5 px-4 py-2 rounded-full text-[10px] font-black uppercase tracking-wider border border-red-500/30 text-red-400 hover:bg-red-500/10 disabled:opacity-40 transition-all"
              >
                {busyId === c.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <XCircle className="w-3.5 h-3.5" />} Ki (Reject)
              </button>
              <button
                onClick={() => review(c.id, 'approve')}
                disabled={busyId === c.id}
                className="flex items-center gap-1.5 px-4 py-2 rounded-full text-[10px] font-black uppercase tracking-wider bg-dyn-accent text-dyn-bg-primary hover:scale-105 active:scale-95 disabled:opacity-40 disabled:hover:scale-100 transition-all"
              >
                {busyId === c.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />} Amince (Approve)
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
