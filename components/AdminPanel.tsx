import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { gemini } from '../services/localService.ts';
import { ArewaLogo } from './ArewaLogo.tsx';
import { CorrectionsReview } from './CorrectionsReview.tsx';
import { LogOut } from 'lucide-react';

export const AdminPanel: React.FC = () => {
  const navigate = useNavigate();
  const [username, setUsername] = useState<string | null | 'loading'>('loading');

  useEffect(() => {
    let cancelled = false;
    gemini.adminMe().then((u) => {
      if (cancelled) return;
      if (u === null) {
        navigate('/admin/login', { replace: true });
      } else {
        setUsername(u);
      }
    });
    return () => { cancelled = true; };
  }, [navigate]);

  const logout = async () => {
    await gemini.adminLogout();
    navigate('/admin/login', { replace: true });
  };

  if (username === 'loading' || username === null) {
    return (
      <div className="vibe-classic h-screen w-full flex items-center justify-center bg-dyn-bg-primary text-dyn-text-muted text-sm">
        Ana tabbatarwa... (Checking session...)
      </div>
    );
  }

  return (
    <div className="vibe-classic h-screen w-full flex flex-col bg-dyn-bg-primary text-dyn-text-primary font-sans">
      <header className="px-6 sm:px-10 py-5 flex items-center justify-between border-b border-dyn-border/40">
        <div className="flex items-center gap-3">
          <ArewaLogo size={36} active />
          <div>
            <h1 className="font-serif italic text-xl text-dyn-accent tracking-tighter leading-none">Murya Admin</h1>
            <p className="text-[9px] uppercase tracking-[0.3em] text-dyn-text-muted mt-0.5">Corrections Review</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs text-dyn-text-secondary font-mono">{username}</span>
          <button
            onClick={logout}
            className="flex items-center gap-1.5 px-4 py-2 rounded-full text-[10px] font-black uppercase tracking-wider border border-dyn-border text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5 transition-all"
          >
            <LogOut className="w-3.5 h-3.5" /> Fita (Logout)
          </button>
        </div>
      </header>
      <main className="flex-1 overflow-y-auto p-6 sm:p-10 max-w-4xl w-full mx-auto">
        <CorrectionsReview />
      </main>
    </div>
  );
};
