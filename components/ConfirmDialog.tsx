import React, { useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  /** True for delete-style destructive actions (red confirm button). */
  danger?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * Small reusable confirmation modal for destructive admin actions (delete
 * corrections/pronunciation/Q&A items). Replaces the browser's native
 * confirm() previously used in QAReview.tsx/PronunciationReview.tsx — a
 * plain confirm() can't be styled or localized consistently with the rest
 * of the admin UI, is blocking (freezes the tab), and gives no way to show
 * a "deleting…" state while the request is in flight. Follows the same
 * dialog conventions as NeuralReview.tsx's modal (role="dialog",
 * aria-modal, Escape to dismiss, backdrop click to cancel).
 */
export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  open, title, message, confirmLabel = 'Tabbatar (Confirm)', cancelLabel = 'Soke (Cancel)',
  danger = true, busy = false, onConfirm, onCancel,
}) => {
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !busy) onCancel();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, busy, onCancel]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center p-4 animate-reveal">
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={() => !busy && onCancel()}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="relative w-full max-w-sm bg-dyn-bg-secondary border border-dyn-border rounded-3xl shadow-2xl p-6 space-y-4 z-10"
      >
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-full shrink-0 ${danger ? 'bg-red-500/15 text-red-400' : 'bg-dyn-accent/15 text-dyn-accent'}`}>
            <AlertTriangle className="w-4 h-4" />
          </div>
          <h3 className="font-serif italic text-lg text-dyn-text-primary">{title}</h3>
        </div>
        <p className="text-sm text-dyn-text-secondary leading-relaxed">{message}</p>
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            onClick={onCancel}
            disabled={busy}
            className="px-4 py-2 rounded-full text-[10px] font-black uppercase tracking-wider border border-dyn-border text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5 disabled:opacity-40 transition-all"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            disabled={busy}
            className={`px-4 py-2 rounded-full text-[10px] font-black uppercase tracking-wider transition-all disabled:opacity-40 ${
              danger
                ? 'bg-red-500/90 text-white hover:bg-red-500'
                : 'bg-dyn-accent text-dyn-bg-primary hover:scale-105 active:scale-95'
            }`}
          >
            {busy ? 'Ana share...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};
