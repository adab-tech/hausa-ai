import React from 'react';
import { Clock, MicOff } from 'lucide-react';

interface LiveCallPanelProps {
  voiceStatus: 'idle' | 'requesting_permission' | 'connecting' | 'connected' | 'error';
  callDuration: number;
  onHangup: () => void;
}

const formatDuration = (sec: number) => {
  const mins = Math.floor(sec / 60);
  const secs = sec % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

export const LiveCallPanel: React.FC<LiveCallPanelProps> = ({ voiceStatus, callDuration, onHangup }) => {
  return (
    <div className="absolute top-0 left-0 right-0 z-30 bg-red-950/95 text-white backdrop-blur-2xl border-b border-red-500/50 px-6 py-4 flex items-center justify-between shadow-2xl animate-reveal">
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
  );
};
