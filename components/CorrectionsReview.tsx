import React, { useEffect, useState } from 'react';
import { gemini } from '../services/localService.ts';
import { CheckCircle2, XCircle } from 'lucide-react';

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
    const ok = await gemini.reviewCorrection(id, action);
    if (ok) {
      setPending(prev => (prev ? prev.filter(c => c.id !== id) : prev));
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
          <div className="flex items-center justify-between pt-3 border-t border-dyn-border/30">
            <span className="text-[9px] font-mono text-dyn-text-muted">{new Date(c.timestamp * 1000).toLocaleString()}</span>
            <div className="flex gap-3">
              <button
                onClick={() => review(c.id, 'reject')}
                className="flex items-center gap-1.5 px-4 py-2 rounded-full text-[10px] font-black uppercase tracking-wider border border-red-500/30 text-red-400 hover:bg-red-500/10 transition-all"
              >
                <XCircle className="w-3.5 h-3.5" /> Ki (Reject)
              </button>
              <button
                onClick={() => review(c.id, 'approve')}
                className="flex items-center gap-1.5 px-4 py-2 rounded-full text-[10px] font-black uppercase tracking-wider bg-dyn-accent text-dyn-bg-primary hover:scale-105 active:scale-95 transition-all"
              >
                <CheckCircle2 className="w-3.5 h-3.5" /> Amince (Approve)
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
