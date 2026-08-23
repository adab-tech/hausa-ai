import React, { useEffect } from 'react';
import { AlertTriangle, X } from 'lucide-react';

export interface ToastItem {
  id: string;
  message: string;
  /** 'error' gets a warning glyph + red-tinted edge; 'info' stays on-brand gold. */
  variant?: 'error' | 'info';
}

/**
 * On-brand replacement for window.alert(). The app is a fully custom
 * obsidian/gold surface everywhere else (chat, dictionary, document tool
 * modals) — a bare OS alert() for mic-permission errors was the one place
 * that broke out of it with an unstyled native dialog that also freezes the
 * whole page until dismissed. This is non-blocking, dismissible, on-brand,
 * and respects prefers-reduced-motion via the existing global rule in
 * index.css (animate-reveal's duration collapses there already).
 */
export const ToastHost: React.FC<{ toasts: ToastItem[]; onDismiss: (id: string) => void }> = ({ toasts, onDismiss }) => {
  if (toasts.length === 0) return null;
  return (
    <div
      className="fixed bottom-32 left-1/2 -translate-x-1/2 z-[200] w-[calc(100%-2rem)] max-w-md flex flex-col gap-3 pointer-events-none"
      aria-live="assertive"
      role="region"
    >
      {toasts.map((t) => (
        <ToastCard key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>
  );
};

const ToastCard: React.FC<{ toast: ToastItem; onDismiss: (id: string) => void }> = ({ toast, onDismiss }) => {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(toast.id), 6000);
    return () => clearTimeout(timer);
  }, [toast.id, onDismiss]);

  const isError = toast.variant !== 'info';

  return (
    <div
      role="alert"
      className={`pointer-events-auto manuscript-bubble rounded-2xl px-5 py-4 flex items-start gap-3 animate-reveal ${isError ? 'border-l-[3px] border-l-red-500/70' : 'border-l-[3px] border-l-dyn-accent'}`}
    >
      <AlertTriangle className={`w-4 h-4 mt-0.5 shrink-0 ${isError ? 'text-red-400' : 'text-dyn-accent'}`} />
      <p className="flex-1 text-sm text-dyn-text-primary leading-relaxed whitespace-pre-line">{toast.message}</p>
      <button
        onClick={() => onDismiss(toast.id)}
        aria-label="Rufe saƙo (Dismiss)"
        className="shrink-0 p-1 -m-1 rounded-lg text-dyn-text-muted hover:text-dyn-text-primary hover:bg-white/5 transition-colors"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
};
