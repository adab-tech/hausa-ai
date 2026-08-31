import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Headphones, X } from 'lucide-react';

/** A one-time, dismissible nudge toward the MOS listening test (/listen),
 * shown after a user has actually heard the voice a few times in this
 * session — not on first load, not repeated once seen or dismissed. See
 * components/MosListen.tsx / backend/mos_store.py. Deliberately its own
 * small component rather than reusing Toast.tsx: the toast system is
 * plain-text + auto-dismiss, and this needs a persistent, clickable link. */
export const MosPrompt: React.FC<{ onDismiss: () => void }> = ({ onDismiss }) => {
  const navigate = useNavigate();

  return (
    <div
      role="region"
      aria-label="Gwajin Murya (listening-test invitation)"
      className="fixed bottom-32 left-1/2 -translate-x-1/2 z-[190] w-[calc(100%-2rem)] max-w-md pointer-events-none"
    >
      <div className="pointer-events-auto manuscript-bubble rounded-2xl px-5 py-4 flex items-start gap-3 animate-reveal border-l-[3px] border-l-dyn-accent">
        <Headphones className="w-4 h-4 mt-0.5 shrink-0 text-dyn-accent" />
        <div className="flex-1 min-w-0">
          <p className="text-sm text-dyn-text-primary leading-relaxed">
            Yaya muryar Murya take sauti a gare ka? (How does Murya's voice sound to you?)
          </p>
          <button
            onClick={() => { onDismiss(); navigate('/listen'); }}
            className="mt-2 text-xs font-bold uppercase tracking-wider text-dyn-accent hover:underline"
          >
            Gwajin sauti na mintuna 5 (5-min listening test) →
          </button>
        </div>
        <button
          onClick={onDismiss}
          aria-label="Rufe saƙo (Dismiss)"
          className="shrink-0 p-1 -m-1 rounded-lg text-dyn-text-muted hover:text-dyn-text-primary hover:bg-white/5 transition-colors"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
