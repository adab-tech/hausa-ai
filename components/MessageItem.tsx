import React, { memo, useState } from 'react';
import { Message, Role } from '../types.ts';
import { GroundingNode } from './GroundingNode.tsx';
import { CheckCircle2, ChevronRight, Play, Square, ThumbsUp, ThumbsDown, Send } from 'lucide-react';

export const AXIOM_PHRASES = [
  "Ana nazarin harshe da al'adu...",
  "Murya na yin tunani sosai...",
  "Ana daidaita sautin murya...",
  "Ana shirya hikimar karin magana...",
  "Ana daidaita ingancin harshe...",
  "Murya na aiki, jira kaɗan...",
  "Ana tattara bayanan tarihi...",
  "Jimawa kaɗan, amsawa ta zo..."
];

// Memoized message item for performant rendering
export const MessageItem = memo(({
  m,
  currentAxiomIndex,
  onFeedback,
  feedback,
  onPlaySpeech,
  playingSpeechId,
  allowTrace = false,
}: {
  m: Message;
  currentAxiomIndex: number;
  onFeedback?: (id: string, type: 'up' | 'down', correction?: string) => void;
  feedback?: 'up' | 'down';
  onPlaySpeech?: (text: string, id: string, normalized?: string) => void;
  playingSpeechId?: string | null;
  /** Global "Advanced" setting (off by default) — most users never need to
   *  see the normalization/tone breakdown on every message. */
  allowTrace?: boolean;
}) => {
  const [showTrace, setShowTrace] = useState(false);
  // Inline, on-brand replacement for window.prompt() — a bare OS dialog
  // looked completely out of place inside this custom manuscript-styled
  // bubble. Opens a small themed panel instead; "Tsallake" still records
  // the down-vote with no correction text, same as leaving prompt() blank.
  const [showCorrectionInput, setShowCorrectionInput] = useState(false);
  const [correctionText, setCorrectionText] = useState('');

  return (
    <div className={`flex ${m.role === Role.user ? 'justify-end' : 'justify-start'} animate-reveal w-full`}>
      <div className={`max-w-[95%] sm:max-w-[85%] w-full flex flex-col ${m.role === Role.user ? 'items-end' : 'items-start'}`}>

        {/* Meta Header */}
        <div className="mb-2 flex items-center gap-3 px-4 opacity-50 text-[10px] uppercase font-bold tracking-wider text-dyn-text-secondary">
          <span>{m.role === Role.user ? 'Umarni / User' : 'Murya Artifact'}</span>
          <span className="h-[1px] w-4 bg-dyn-border"></span>
          {m.verified && (
             <span className="flex items-center gap-1 text-dyn-accent border border-dyn-accent/40 px-2 py-0.5 rounded-md bg-dyn-accent/5 animate-pulse text-[9px] font-black">
                <CheckCircle2 className="w-3 h-3" />
                FADA-CERTIFIED
             </span>
          )}
          <span className="font-mono text-[9px]">{new Date(m.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
        </div>

        {/* The Manuscript Bubble */}
        <div className={`w-full p-6 sm:p-10 rounded-[30px] manuscript-bubble transition-all duration-500 hover:shadow-[0_15px_30px_rgba(0,0,0,0.6)] ${m.role === Role.assistant ? 'border-l-[6px] border-l-dyn-accent' : 'bg-white/[0.02]'}`}>
          {m.isThinking && m.text === "" ? (
            <div className="flex flex-col gap-4 py-4">
               <div className="flex items-center gap-4">
                  <div className="w-6 h-6 rounded-full border-2 border-dyn-accent border-t-transparent animate-spin"></div>
                  <span className="text-lg font-serif italic text-dyn-text-secondary">{AXIOM_PHRASES[currentAxiomIndex]}</span>
               </div>
               <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                  <div className="h-full bg-dyn-accent/50 animate-[drift_3s_linear_infinite]" style={{ width: '45%' }}></div>
               </div>
            </div>
          ) : (
            <div className={`text-xl sm:text-2xl md:text-3xl leading-[1.6] break-words whitespace-pre-wrap ${m.role === Role.assistant ? 'font-serif not-italic text-dyn-text-primary selection:bg-dyn-accent/40' : 'font-sans text-dyn-text-secondary'}`}>
              {m.text}
            </div>
          )}

          {m.groundingSources && m.groundingSources.length > 0 && <GroundingNode sources={m.groundingSources} />}

          {m.attachments && m.attachments.length > 0 && (
            <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-6">
              {m.attachments.map((at, i) => (
                <div key={i} className="rounded-2xl overflow-hidden border border-dyn-border shadow-2xl relative group bg-black/40 shimmer">
                  {at.type === 'image' && <img src={at.data} alt={at.name || 'Hoto (generated or attached image)'} className="w-full h-auto max-h-[300px] object-cover group-hover:scale-105 transition-all duration-1000" loading="lazy" />}
                  {at.type === 'video' && <video src={at.uri || at.data} controls className="w-full h-auto max-h-[300px]" />}
                  <div className="absolute bottom-4 left-4 px-3 py-1.5 bg-black/80 backdrop-blur-md border border-dyn-border rounded-full text-[9px] font-bold uppercase tracking-wider text-dyn-accent opacity-0 group-hover:opacity-100 transition-opacity">
                    {at.name}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Saurara (listen) + optional Advanced trace toggle */}
          {m.role === Role.assistant && !m.isThinking && (
            <div className="mt-6 border-t border-dyn-border/40 pt-5 text-left flex flex-col gap-4">
              <div className="flex items-center justify-between w-full flex-wrap gap-2">
                {allowTrace && (m.normalized || m.toneMapped) ? (
                  <button
                    onClick={() => setShowTrace(!showTrace)}
                    className="flex items-center gap-2 text-xs text-dyn-accent/80 hover:text-dyn-accent transition-colors focus:outline-none"
                  >
                    <ChevronRight className={`w-3.5 h-3.5 transform transition-transform duration-300 ${showTrace ? 'rotate-90' : 'rotate-0'}`} />
                    <span>Hanya / Linguistic Trace</span>
                  </button>
                ) : <span />}

                <div className="flex items-center gap-3">
                  {onPlaySpeech && (
                    <button
                      onClick={() => onPlaySpeech(m.text, m.id, m.normalized)}
                      className={`relative flex items-center gap-1.5 text-xs transition-all focus:outline-none px-3 py-1 rounded-full border before:content-[''] before:absolute before:-inset-y-2.5 before:-inset-x-1.5 ${
                        playingSpeechId === m.id
                          ? 'bg-dyn-accent text-dyn-bg-primary border-dyn-accent shadow-[0_0_12px_rgba(var(--accent-gold-rgb),0.3)] animate-pulse'
                          : 'bg-dyn-accent/10 border-dyn-accent/20 text-dyn-accent hover:bg-dyn-accent/20 hover:scale-105 active:scale-95'
                      }`}
                      title={playingSpeechId === m.id ? 'Dakata (Stop)' : 'Saurara da muryar AI (Listen with AI voice)'}
                    >
                      {playingSpeechId === m.id
                        ? <Square className="w-3 h-3 fill-current" />
                        : <Play className="w-3.5 h-3.5 fill-current" />}
                      <span>{playingSpeechId === m.id ? 'Dakata' : 'Saurara'}</span>
                    </button>
                  )}

                {onFeedback && (
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => onFeedback(m.id, 'up')}
                      disabled={!!feedback}
                      className={`relative p-2 rounded-xl transition-all before:content-[''] before:absolute before:-inset-1.5 ${feedback === 'up' ? 'bg-green-500/20 text-green-400 font-bold border border-green-500/30' : feedback ? 'opacity-30 cursor-not-allowed' : 'text-dyn-text-secondary hover:text-green-400 hover:bg-white/5 border border-transparent'}`}
                      title={feedback === 'up' ? 'An adana amsa mai kyau' : 'Amsa mai kyau (Thumbs Up)'}
                    >
                      <ThumbsUp className="w-4.5 h-4.5" />
                    </button>
                    <button
                      onClick={() => setShowCorrectionInput(v => !v)}
                      disabled={!!feedback}
                      className={`relative p-2 rounded-xl transition-all before:content-[''] before:absolute before:-inset-1.5 ${feedback === 'down' ? 'bg-red-500/20 text-red-400 font-bold border border-red-500/30' : feedback ? 'opacity-30 cursor-not-allowed' : showCorrectionInput ? 'bg-white/5 text-red-400 border border-dyn-border' : 'text-dyn-text-secondary hover:text-red-400 hover:bg-white/5 border border-transparent'}`}
                      title={feedback === 'down' ? 'An adana kuskure' : 'Amsa ba daidai ba (Thumbs Down)'}
                    >
                      <ThumbsDown className="w-4.5 h-4.5" />
                    </button>
                  </div>
                )}
                </div>

                {showCorrectionInput && !feedback && (
                  <div className="w-full p-4 rounded-2xl bg-black/50 border border-dyn-border/30 space-y-3 animate-reveal">
                    <label className="text-[10px] uppercase tracking-wider text-dyn-text-muted font-bold block">
                      Me ya kamata amsar ta kasance? (Optional — leave blank to just flag it)
                    </label>
                    <textarea
                      value={correctionText}
                      onChange={(e) => setCorrectionText(e.target.value)}
                      rows={2}
                      autoFocus
                      placeholder="Rubuta gyara anan… (Write the correction here…)"
                      className="w-full bg-white/[0.02] border border-dyn-border rounded-xl px-3.5 py-2.5 text-sm text-dyn-text-primary focus:outline-none focus:border-dyn-accent/50 placeholder:text-dyn-text-muted/40 resize-none no-scrollbar"
                    />
                    <div className="flex items-center justify-end flex-wrap gap-2">
                      <button
                        onClick={() => { setShowCorrectionInput(false); setCorrectionText(''); onFeedback?.(m.id, 'down', undefined); }}
                        className="px-3.5 py-2 rounded-xl text-xs font-bold uppercase tracking-wider whitespace-nowrap text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5 transition-colors"
                      >
                        Tsallake (Skip)
                      </button>
                      <button
                        onClick={() => { const c = correctionText.trim(); setShowCorrectionInput(false); setCorrectionText(''); onFeedback?.(m.id, 'down', c || undefined); }}
                        className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-wider whitespace-nowrap shrink-0 bg-dyn-accent/15 text-dyn-accent border border-dyn-accent/30 hover:bg-dyn-accent/25 transition-colors"
                      >
                        <Send className="w-3.5 h-3.5 shrink-0" />
                        Aika (Submit)
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {showTrace && (
                <div className="mt-4 p-5 rounded-2xl bg-black/50 border border-dyn-border/30 space-y-4 text-xs animate-reveal font-mono">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-3.5 rounded-xl bg-white/[0.01] border border-white/5">
                      <span className="text-[8px] uppercase tracking-wider text-dyn-text-muted block mb-1.5 font-bold">Original Generation</span>
                      <p className="font-serif not-italic text-dyn-text-primary/90">{m.text}</p>
                    </div>
                    <div className="p-3.5 rounded-xl bg-white/[0.01] border border-white/5">
                      <span className="text-[8px] uppercase tracking-wider text-dyn-accent/50 block mb-1.5 font-bold">Normalized (ɗ, ɓ, ƙ, ƴ)</span>
                      <p className="font-serif not-italic text-dyn-accent">{m.normalized || m.text}</p>
                    </div>
                    <div className="p-3.5 rounded-xl bg-white/[0.01] border border-white/5">
                      <span className="text-[8px] uppercase tracking-wider text-dyn-text-muted block mb-1.5 font-bold">Tonal Melody (R→L Pitch)</span>
                      <p className="font-serif not-italic text-dyn-text-secondary">{m.toneMapped || "Babu lambar sauti"}</p>
                    </div>
                  </div>
                  <div className="text-[8px] text-dyn-text-muted uppercase tracking-[0.2em] text-right">
                    Litvinova Mora TBU Logic: Active
                  </div>
                </div>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  );
});
