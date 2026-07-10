import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { gemini } from '../services/localService.ts';
import { ArewaLogo } from './ArewaLogo.tsx';
import { KeyRound } from 'lucide-react';

export const AdminLogin: React.FC = () => {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!username.trim() || !password) return;
    setLoading(true);
    setError(null);
    const result = await gemini.adminLogin(username.trim(), password);
    setLoading(false);
    if ('error' in result) {
      setError(result.error);
      return;
    }
    navigate('/admin');
  };

  return (
    <div className="vibe-classic h-screen w-full flex items-center justify-center bg-dyn-bg-primary text-dyn-text-primary font-sans px-6">
      <div className="w-full max-w-sm space-y-8 animate-reveal">
        <div className="flex flex-col items-center gap-4 text-center">
          <ArewaLogo size={56} active />
          <div>
            <h1 className="font-serif italic text-3xl text-dyn-accent tracking-tighter">Murya Admin</h1>
            <p className="text-[9px] uppercase tracking-[0.3em] text-dyn-text-muted mt-1">Reviewer Sign-In</p>
          </div>
        </div>

        <div className="space-y-4">
          <input
            type="text"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') submit(); }}
            placeholder="Sunan mai amfani (Username)"
            className="w-full px-4 py-3 bg-dyn-bg-tertiary/60 border border-dyn-border rounded-2xl text-sm text-dyn-text-primary focus:outline-none focus:border-dyn-accent/50"
          />
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') submit(); }}
            placeholder="Kalmar sirri (Password)"
            className="w-full px-4 py-3 bg-dyn-bg-tertiary/60 border border-dyn-border rounded-2xl text-sm text-dyn-text-primary focus:outline-none focus:border-dyn-accent/50"
          />

          {error && (
            <p role="alert" className="text-xs text-red-400 text-center">{error}</p>
          )}

          <button
            onClick={submit}
            disabled={loading || !username.trim() || !password}
            className="w-full flex items-center justify-center gap-2 px-8 py-3 rounded-full bg-dyn-accent text-dyn-bg-primary text-[10px] font-black uppercase tracking-widest hover:scale-[1.02] active:scale-95 transition-all disabled:opacity-40 disabled:pointer-events-none"
          >
            <KeyRound className="w-3.5 h-3.5" />
            {loading ? 'Ana shiga...' : 'Shiga (Sign In)'}
          </button>
        </div>

        <p className="text-[10px] text-dyn-text-muted italic text-center">
          Wannan shafi don masu bita ne kawai. (This page is for reviewers only.)
        </p>
      </div>
    </div>
  );
};
