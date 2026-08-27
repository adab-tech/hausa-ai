import React, { useState, useEffect } from 'react';
import { WifiOff, CheckCircle2 } from 'lucide-react';

export const OfflineBanner: React.FC = () => {
  const [isOffline, setIsOffline] = useState(false);
  const [justReconnected, setJustReconnected] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleOffline = () => {
      setIsOffline(true);
      setJustReconnected(false);
    };

    const handleOnline = () => {
      setIsOffline(false);
      setJustReconnected(true);
      setTimeout(() => setJustReconnected(false), 4000);
    };

    setIsOffline(!navigator.onLine);

    window.addEventListener('offline', handleOffline);
    window.addEventListener('online', handleOnline);

    return () => {
      window.removeEventListener('offline', handleOffline);
      window.removeEventListener('online', handleOnline);
    };
  }, []);

  if (justReconnected) {
    return (
      <div className="fixed top-3 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-full bg-emerald-950/90 border border-emerald-500/40 text-emerald-300 text-xs font-mono flex items-center gap-2 shadow-2xl backdrop-blur-md animate-fade-in">
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
        <span>Intanet ya dawo. An sake haɗa Murya da cibiyar sauti.</span>
      </div>
    );
  }

  if (!isOffline) return null;

  return (
    <div className="fixed top-3 left-1/2 -translate-x-1/2 z-50 max-w-lg w-[92%] px-4 py-2.5 rounded-xl bg-[#181102]/95 border border-amber-500/50 text-amber-200 text-xs font-mono flex items-center justify-between shadow-2xl backdrop-blur-md animate-fade-in">
      <div className="flex items-center gap-2.5">
        <WifiOff className="w-4 h-4 text-amber-400 shrink-0" />
        <span className="leading-tight">
          <strong>Yanayin Na'ura (Offline):</strong> Kana iya bincika Ƙamus da duba bayanan da ka adana.
        </span>
      </div>
      <span className="text-[10px] font-bold text-amber-400/80 uppercase tracking-wider px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 shrink-0 ml-2">
        Ƙamus Ready
      </span>
    </div>
  );
};
