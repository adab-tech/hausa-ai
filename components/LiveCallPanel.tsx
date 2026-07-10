import React from 'react';
import { Clock, MicOff } from 'lucide-react';

interface LiveCallPanelProps {
  voiceStatus: 'idle' | 'requesting_permission' | 'connecting' | 'connected' | 'error';
  callDuration: number;
  liveTranscripts: Array<{ role: 'user' | 'assistant'; text: string }>;
  onHangup: () => void;
}

const formatDuration = (sec: number) => {
  const mins = Math.floor(sec / 60);
  const secs = sec % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

export const LiveCallPanel: React.FC<LiveCallPanelProps> = ({ voiceStatus, callDuration, liveTranscripts, onHangup }) => {
  return (
    <div className="absolute top-0 left-0 right-0 z-30 bg-red-950/95 text-white backdrop-blur-2xl border-b border-red-500/50 px-6 py-4 flex flex-col gap-4 shadow-2xl animate-reveal max-h-[40vh] overflow-hidden">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="relative flex h-3.5 w-3.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-red-500"></span>
          </span>
          <div className="flex flex-col">
            <span className="text-[10px] uppercase font-bold tracking-widest text-red-300">Sautin Murya (Live Voice Session)</span>
            <span className="text-sm font-serif italic text-white/90">
              {voiceStatus === 'connecting' ? 'Ana haɗawa...' : voiceStatus === 'connected' ? 'Haɗin kai tsaye: Yi magana da Hausa' : 'Ana neman izini...'}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div className="text-xs font-mono flex items-center gap-1.5 bg-black/30 px-3 py-1 rounded-full border border-white/10">
            <Clock className="w-3.5 h-3.5 text-red-400" />
            {formatDuration(callDuration)}
          </div>
          <button
            onClick={onHangup}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-full text-[10px] font-black uppercase tracking-wider active:scale-95 transition-all shadow-md flex items-center gap-1.5 border border-red-500/40"
          >
            <MicOff className="w-3.5 h-3.5" />
            <span>Kashe (Hangup)</span>
          </button>
        </div>
      </div>

      {/* Transcript Panel */}
      <div className="flex-1 overflow-y-auto bg-black/40 rounded-2xl p-4 border border-white/5 space-y-3 max-h-[22vh] no-scrollbar">
        {liveTranscripts.length === 0 ? (
          <div className="text-center text-xs text-white/40 italic py-4">Fara magana, rubutu zai bayyana anan...</div>
        ) : (
          liveTranscripts.map((t, idx) => (
            <div key={idx} className={`flex flex-col ${t.role === 'user' ? 'items-end' : 'items-start'} animate-reveal`}>
              <span className="text-[8px] uppercase tracking-wider opacity-40 font-mono mb-0.5">{t.role === 'user' ? 'Kai (User)' : 'Murya'}</span>
              <div className={`px-4 py-2 rounded-2xl text-sm max-w-[85%] ${t.role === 'user' ? 'bg-white/10 text-white' : 'bg-red-900/40 text-red-100 border border-red-800/50 font-serif italic'}`}>
                {t.text}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
