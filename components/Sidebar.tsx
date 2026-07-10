import React from 'react';
import { SovereignVibe } from '../types.ts';
import { ArewaLogo } from './ArewaLogo.tsx';
import { Sliders, Volume2, ChevronRight, Activity, BookOpen, Cpu, X, Trash2 } from 'lucide-react';

interface SidebarProps {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  isLoading: boolean;
  isLiveActive: boolean;
  vibe: SovereignVibe;
  setVibe: (v: SovereignVibe) => void;
  showVibeDial: boolean;
  setShowVibeDial: (v: boolean) => void;
  speakerId: number | null;
  setSpeakerId: (id: number | null) => void;
  showSpeakerDial: boolean;
  setShowSpeakerDial: (v: boolean) => void;
  onOpenReview: () => void;
  onOpenWhitePaper: () => void;
  onClearChat: () => void;
  hasMessages: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sidebarOpen,
  setSidebarOpen,
  isLoading,
  isLiveActive,
  vibe,
  setVibe,
  showVibeDial,
  setShowVibeDial,
  speakerId,
  setSpeakerId,
  showSpeakerDial,
  setShowSpeakerDial,
  onOpenReview,
  onOpenWhitePaper,
  onClearChat,
  hasMessages,
}) => {
  return (
    <>
      <aside className={`fixed md:relative top-0 bottom-0 left-0 z-50 w-[290px] bg-dyn-bg-secondary/90 md:bg-dyn-bg-secondary/40 border-r border-dyn-border backdrop-blur-xl md:backdrop-blur-md flex flex-col justify-between p-6 transition-all duration-500 ease-in-out ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}>
        <div className="space-y-8">

          {/* Brand Logo & Header */}
          <div className="flex items-center gap-4 border-b border-dyn-border/40 pb-5">
            <ArewaLogo size={42} active={isLoading || isLiveActive} />
            <div className="flex flex-col">
              <h1 className="font-serif italic text-3xl text-dyn-accent tracking-tighter leading-none">Hausa AI</h1>
              <span className="text-[9px] text-dyn-text-muted uppercase tracking-[0.25em] font-bold mt-1.5 flex items-center gap-1.5">
                <Cpu className="w-3 h-3 text-dyn-accent shrink-0" /> Murya
              </span>
            </div>
            <button onClick={() => setSidebarOpen(false)} aria-label="Rufe menu (Close menu)" className="md:hidden ml-auto p-1 text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5 rounded-lg">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Configuration Options */}
          <div className="space-y-6">
            <div className="space-y-2">
              <label className="text-[9px] uppercase tracking-wider text-dyn-text-muted font-bold flex items-center gap-1.5">
                <Sliders className="w-3 h-3 text-dyn-accent" /> Sovereign Vibe / Protocol
              </label>

              <div className="relative">
                <button
                  onClick={() => { setShowVibeDial(!showVibeDial); setShowSpeakerDial(false); }}
                  className="w-full px-4 py-3 bg-dyn-bg-tertiary/60 border border-dyn-border rounded-2xl text-xs font-bold uppercase tracking-wider text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-dyn-bg-tertiary transition-all flex items-center justify-between"
                >
                  <span>Protocol: {vibe}</span>
                  <ChevronRight className={`w-4 h-4 transform transition-transform ${showVibeDial ? 'rotate-90' : 'rotate-0'}`} />
                </button>
                {showVibeDial && (
                  <div className="absolute top-14 left-0 right-0 bg-dyn-bg-tertiary/95 border border-dyn-border rounded-2xl p-2 shadow-2xl z-[100] animate-reveal backdrop-blur-xl">
                    {(['Classic', 'Royal', 'Cyberpunk', 'Academic'] as SovereignVibe[]).map(v => (
                      <button
                        key={v}
                        onClick={() => { setVibe(v); setShowVibeDial(false); }}
                        className={`w-full text-left px-4 py-2.5 rounded-xl text-xs uppercase tracking-wider transition-all ${vibe === v ? 'bg-dyn-accent/15 text-dyn-accent font-bold' : 'text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5'}`}
                      >
                        {v}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-[9px] uppercase tracking-wider text-dyn-text-muted font-bold flex items-center gap-1.5">
                <Volume2 className="w-3 h-3 text-dyn-accent" /> Murya / TTS Speaker
              </label>

              <div className="relative">
                <button
                  onClick={() => { setShowSpeakerDial(!showSpeakerDial); setShowVibeDial(false); }}
                  className="w-full px-4 py-3 bg-dyn-bg-tertiary/60 border border-dyn-border rounded-2xl text-xs font-bold uppercase tracking-wider text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-dyn-bg-tertiary transition-all flex items-center justify-between"
                >
                  <span className="truncate">{speakerId === null ? 'Baseline (Piper)' : `Speaker ${speakerId + 1} (${speakerId < 4 ? 'Namiji' : 'Mace'})`}</span>
                  <ChevronRight className={`w-4 h-4 transform transition-transform ${showSpeakerDial ? 'rotate-90' : 'rotate-0'}`} />
                </button>
                {showSpeakerDial && (
                  <div className="absolute top-14 left-0 right-0 bg-dyn-bg-tertiary/98 border border-dyn-border rounded-2xl p-2 shadow-2xl z-[100] animate-reveal backdrop-blur-xl max-h-[30vh] overflow-y-auto no-scrollbar">
                    <button
                      onClick={() => { setSpeakerId(null); setShowSpeakerDial(false); }}
                      className={`w-full text-left px-4 py-2 rounded-xl text-[10px] uppercase tracking-wider transition-all ${speakerId === null ? 'bg-dyn-accent/15 text-dyn-accent font-bold' : 'text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5'}`}
                    >
                      Baseline (Piper)
                    </button>
                    <div className="h-[1px] bg-dyn-border my-1.5"></div>
                    {Array.from({length: 8}, (_, i) => (
                      <button
                        key={i}
                        onClick={() => { setSpeakerId(i); setShowSpeakerDial(false); }}
                        className={`w-full text-left px-4 py-2 rounded-xl text-[10px] uppercase tracking-wider transition-all ${speakerId === i ? 'bg-dyn-accent/15 text-dyn-accent font-bold' : 'text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5'}`}
                      >
                        Murya {i < 4 ? `M${i + 1} (Namiji)` : `F${i - 3} (Mace)`} · WAXAL
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Action Links */}
          <div className="space-y-3 pt-6 border-t border-dyn-border/40">
            <button
              onClick={() => { onOpenReview(); setSidebarOpen(false); }}
              className="w-full py-3 px-4 bg-white/5 hover:bg-white/10 text-dyn-text-primary border border-dyn-border rounded-2xl text-[11px] font-black uppercase tracking-wider transition-all flex items-center gap-3 shadow-sm"
            >
              <Activity className="w-4 h-4 text-dyn-accent" />
              <span>Matattarar Bayanai</span>
            </button>
            <button
              onClick={() => { onOpenWhitePaper(); setSidebarOpen(false); }}
              className="w-full py-3 px-4 bg-white/5 hover:bg-white/10 text-dyn-text-primary border border-dyn-border rounded-2xl text-[11px] font-black uppercase tracking-wider transition-all flex items-center gap-3 shadow-sm"
            >
              <BookOpen className="w-4 h-4 text-dyn-accent" />
              <span>White Paper</span>
            </button>
          </div>
        </div>

        {/* System Stats Footer */}
        <div className="space-y-4 border-t border-dyn-border/40 pt-5 text-[10px] font-mono text-dyn-text-muted">
          <div className="flex justify-between">
            <span>Model Tier:</span>
            <span className="text-dyn-accent font-bold">Murya-7 Pro</span>
          </div>
          <div className="flex justify-between">
            <span>Autonomy Level:</span>
            <span className="text-dyn-accent font-bold">FADA Protocol</span>
          </div>
          <button
            onClick={onClearChat}
            disabled={!hasMessages}
            className="w-full py-2.5 border border-red-500/20 hover:border-red-500/40 hover:bg-red-500/5 text-red-500/70 hover:text-red-500 rounded-xl text-[10px] font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 disabled:opacity-20 disabled:cursor-not-allowed"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Goge Hira (Clear)</span>
          </button>
        </div>
      </aside>

      {/* Sidebar overlay backdrop for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </>
  );
};
