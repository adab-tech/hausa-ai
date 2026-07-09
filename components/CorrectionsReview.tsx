import React, { useEffect, useState } from 'react';
import { gemini } from '../services/localService.ts';
import { CheckCircle2, XCircle, KeyRound } from 'lucide-react';

const REVIEWER_KEY_STORAGE = 'hausa_ai_reviewer_key';

interface Correction {
  id: string;
  messageId: string;
  originalText: string;
  correction: string;
  status: 'pending' | 'approved' | 'rejected';
  timestamp: number;
}

/**
 * Human-in-the-loop review queue. Gated by a reviewer key (X-Reviewer-Key),
 * separate from the general API_KEY — this is the one control that decides
 * what the model actually learns from user corrections, so it stays behind
 * its own explicit gate rather than opening whenever the app is unlocked.
 */
export const CorrectionsReview: React.FC = () => {
  const [reviewerKey, setReviewerKey] = useState(() => sessionStorage.getItem(REVIEWER_KEY_STORAGE) || '');
  const [keyInput, setKeyInput] = useState('');
  const [pending, setPending] = useState<Correction[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadPending = async (key: string) => {
    setError(null);
    const data = await gemini.getCorrections('pending', key);
    if (data === null) {
      setError('Ba a iya samun bayanai ba — duba maballin bita (reviewer key).');
      setPending(null);
    } else {
      setPending(data);
    }
  };

  useEffect(() => {
    if (reviewerKey) loadPending(reviewerKey);
  }, [reviewerKey]);

  const unlock = () => {
    sessionStorage.setItem(REVIEWER_KEY_STORAGE, keyInput);
    setReviewerKey(keyInput);
  };

  const review = async (id: string, action: 'approve' | 'reject') => {
    const ok = await gemini.reviewCorrection(id, action, reviewerKey);
    if (ok) {
      setPending(prev => (prev ? prev.filter(c => c.id !== id) : prev));
    }
  };

  if (!reviewerKey) {
    return (
      <div className="max-w-md mx-auto py-12 text-center space-y-6 animate-reveal">
        <KeyRound className="w-10 h-10 text-dyn-accent mx-auto" />
        <p className="text-sm text-dyn-text-secondary">
          Wannan sashe don masu bita ne kawai. Shigar da reviewer key (X-Reviewer-Key) domin ci gaba.
        </p>
        <input
          type="password"
          value={keyInput}
          onChange={(e) => setKeyInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') unlock(); }}
          placeholder="Reviewer key"
          className="w-full px-4 py-3 bg-dyn-bg-tertiary/60 border border-dyn-border rounded-2xl text-sm text-dyn-text-primary focus:outline-none focus:border-dyn-accent/50"
        />
        <button
          onClick={unlock}
          className="px-8 py-3 rounded-full bg-dyn-accent text-dyn-bg-primary text-[10px] font-black uppercase tracking-widest hover:scale-105 active:scale-95 transition-all"
        >
          Buɗe (Unlock)
        </button>
        <p className="text-[10px] text-dyn-text-muted italic">
          Idan ba a saita REVIEWER_API_KEY a backend ba tukuna, kowace shigarwa za ta yi aiki (dev mode).
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-reveal">
      {error && (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => { sessionStorage.removeItem(REVIEWER_KEY_STORAGE); setReviewerKey(''); }} className="text-xs underline">
            Sake shigarwa
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
