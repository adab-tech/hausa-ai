import React, { useEffect, useState } from 'react';
import { KeyRound, X, Eye, EyeOff } from 'lucide-react';
import { gemini } from '../services/localService.ts';

interface ChangePasswordDialogProps {
  open: boolean;
  onClose: () => void;
  /** Called after a successful change -- the backend has already
   * invalidated the current session, so the caller must redirect to
   * login, not just close the dialog. */
  onSuccess: () => void;
}

const MIN_LENGTH = 12;

/**
 * Self-service admin password change. Follows ConfirmDialog.tsx's modal
 * conventions (role="dialog", aria-modal, Escape/backdrop to dismiss) but
 * with real form fields instead of a single confirm action.
 */
export const ChangePasswordDialog: React.FC<ChangePasswordDialogProps> = ({ open, onClose, onSuccess }) => {
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPasswords, setShowPasswords] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setOldPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setError(null);
    setBusy(false);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !busy) onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, busy, onClose]);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < MIN_LENGTH) {
      setError(`Sabuwar kalmar sirri dole ta kai haruffa ${MIN_LENGTH} aƙalla. (New password must be at least ${MIN_LENGTH} characters.)`);
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Kalmomin sirri biyu ba su daidaita ba. (New passwords do not match.)');
      return;
    }
    setBusy(true);
    setError(null);
    const result = await gemini.changePassword(oldPassword, newPassword);
    setBusy(false);
    if (result.ok === false) {
      setError(result.error);
      return;
    }
    onSuccess();
  };

  const inputClass = "w-full bg-dyn-bg-tertiary/60 border border-dyn-border rounded-xl px-4 py-2.5 text-sm text-dyn-text-primary placeholder:text-dyn-text-muted focus:outline-none focus:border-dyn-accent/60 transition-colors";

  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center p-4 animate-reveal">
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={() => !busy && onClose()}
        aria-hidden="true"
      />
      <form
        onSubmit={handleSubmit}
        role="dialog"
        aria-modal="true"
        aria-label="Canja Kalmar Sirri (Change Password)"
        className="relative w-full max-w-sm bg-dyn-bg-secondary border border-dyn-border rounded-3xl shadow-2xl p-6 space-y-4 z-10"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-full shrink-0 bg-dyn-accent/15 text-dyn-accent">
              <KeyRound className="w-4 h-4" />
            </div>
            <h3 className="font-serif italic text-lg text-dyn-text-primary">Canja Kalmar Sirri</h3>
          </div>
          <button
            type="button"
            onClick={() => !busy && onClose()}
            disabled={busy}
            aria-label="Rufe (Close)"
            className="p-1.5 -m-1.5 rounded-lg text-dyn-text-muted hover:text-dyn-text-primary hover:bg-white/5 disabled:opacity-40 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs text-dyn-text-muted leading-relaxed">
          Sauya kalmar sirrin shiga admin. Za a fitar da kai daga kowane zama bayan nasara. (This changes your admin login password. You'll be signed out everywhere on success.)
        </p>

        <div className="space-y-3">
          <div>
            <label htmlFor="cp-old" className="block text-[10px] uppercase tracking-widest text-dyn-text-muted mb-1.5">
              Kalmar sirri ta yanzu (Current password)
            </label>
            <input
              id="cp-old"
              type={showPasswords ? 'text' : 'password'}
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              autoComplete="current-password"
              required
              disabled={busy}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="cp-new" className="block text-[10px] uppercase tracking-widest text-dyn-text-muted mb-1.5">
              Sabuwar kalmar sirri (New password)
            </label>
            <input
              id="cp-new"
              type={showPasswords ? 'text' : 'password'}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
              minLength={MIN_LENGTH}
              required
              disabled={busy}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="cp-confirm" className="block text-[10px] uppercase tracking-widest text-dyn-text-muted mb-1.5">
              Sake rubuta sabuwar kalma (Confirm new password)
            </label>
            <input
              id="cp-confirm"
              type={showPasswords ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              required
              disabled={busy}
              className={inputClass}
            />
          </div>
          <button
            type="button"
            onClick={() => setShowPasswords((s) => !s)}
            className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-dyn-text-muted hover:text-dyn-text-secondary transition-colors"
          >
            {showPasswords ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
            {showPasswords ? 'Ɓoye (Hide)' : 'Nuna (Show)'}
          </button>
        </div>

        {error && (
          <p role="alert" className="text-xs text-red-400 leading-relaxed">{error}</p>
        )}

        <div className="flex items-center justify-end gap-3 pt-1">
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="px-4 py-2 rounded-full text-[10px] font-black uppercase tracking-wider border border-dyn-border text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5 disabled:opacity-40 transition-all"
          >
            Soke (Cancel)
          </button>
          <button
            type="submit"
            disabled={busy}
            className="px-4 py-2 rounded-full text-[10px] font-black uppercase tracking-wider bg-dyn-accent text-dyn-bg-primary hover:scale-105 active:scale-95 disabled:opacity-40 transition-all"
          >
            {busy ? 'Ana canzawa...' : 'Canja (Change)'}
          </button>
        </div>
      </form>
    </div>
  );
};
