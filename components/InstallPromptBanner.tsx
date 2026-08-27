import React, { useState, useEffect } from 'react';
import { X, Smartphone, Sparkles } from 'lucide-react';

export const InstallPromptBanner: React.FC = () => {
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
      // Show prompt after 3 seconds of user engagement if not already installed
      setTimeout(() => setIsVisible(true), 3000);
    };

    window.addEventListener('beforeinstallprompt', handler);

    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') {
      setIsVisible(false);
    }
    setDeferredPrompt(null);
  };

  if (!isVisible) return null;

  return (
    <div className="p-3.5 rounded-xl border border-amber-500/30 bg-[#0E1526]/90 backdrop-blur-md shadow-xl flex items-center justify-between gap-3 text-xs font-mono">
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center shrink-0">
          <Smartphone className="w-4 h-4 text-amber-400" />
        </div>
        <div className="flex flex-col">
          <span className="font-bold text-zinc-100 flex items-center gap-1">
            Sanya Murya a Wayarka
            <Sparkles className="w-3 h-3 text-amber-400" />
          </span>
          <span className="text-[11px] text-zinc-400">
            Aiki ba tare da intanet ba (Offline 30k Ƙamus)
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <button
          onClick={handleInstall}
          className="px-3 py-1.5 rounded-lg bg-amber-500 text-zinc-950 font-bold hover:bg-amber-400 transition-colors shadow-sm cursor-pointer"
        >
          Shigar (Install)
        </button>
        <button
          onClick={() => setIsVisible(false)}
          className="p-1 rounded text-zinc-500 hover:text-zinc-300"
          aria-label="Close"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
