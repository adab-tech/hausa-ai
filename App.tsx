
import React, { useState, useRef, useEffect, useMemo, memo } from 'react';
import { gemini } from './services/localService.ts';
import { Message, Role, Attachment, SovereignVibe } from './types.ts';
import { ArewaLogo } from './components/ArewaLogo.tsx';
import { Waveform } from './components/Waveform.tsx';
import { NeuralReview } from './components/NeuralReview.tsx';
import { GroundingNode } from './components/GroundingNode.tsx';
import { WhitePaper } from './components/WhitePaper.tsx';
import { decodeAudioData, decode, createBlob } from './utils/audio.ts';

const AXIOM_PHRASES = [
  "Duba Matakin Girmamawa (Protocol)...",
  "Checking Tonal Consistency...",
  "Applying Litvinova's Laws...",
  "Synthesizing Proverbial Wisdom...",
  "Optimizing Social Hierarchy...",
  "Vertex Sovereign: Nexus-7 Deep Scan..."
];

const MessageItem = memo(({ m, currentAxiomIndex }: { m: Message; currentAxiomIndex: number }) => {
  return (
    <div className={`flex ${m.role === Role.user ? 'justify-end' : 'justify-start'} animate-reveal w-full`}>
      <div className={`max-w-[95%] sm:max-w-[85%] w-full flex flex-col ${m.role === Role.user ? 'items-end' : 'items-start'}`}>
        
        {/* Meta Header */}
        <div className="mb-4 flex items-center gap-4 px-6 opacity-40 text-[9px] uppercase font-black tracking-widest">
          {m.role === Role.user ? 'Umarni' : 'Sovereign Artifact'}
          <span className="h-[1px] w-6 bg-white/10"></span>
          {m.verified && (
             <span className="flex items-center gap-1.5 text-silk-gold border border-silk-gold/30 px-2 py-0.5 rounded-sm bg-silk-gold/5 animate-pulse">
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z"/></svg>
                FADA-CERTIFIED
             </span>
          )}
          <span className="font-mono text-[8px]">{new Date(m.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
        </div>

        {/* The Manuscript Bubble */}
        <div className={`w-full p-8 sm:p-14 md:p-20 rounded-[40px] sm:rounded-[80px] manuscript-bubble ${m.role === Role.assistant ? 'border-l-[8px] border-l-silk-gold' : 'bg-parchment'}`}>
          {m.isThinking && m.text === "" ? (
            <div className="flex flex-col gap-8 py-10">
               <div className="flex items-center gap-6">
                  <div className="w-8 h-8 rounded-full border-2 border-silk-gold border-t-transparent animate-spin"></div>
                  <div className="flex flex-col gap-1">
                    <span className="text-[12px] uppercase tracking-[0.4em] text-silk-gold font-mono animate-pulse">Neural Trace</span>
                    <span className="text-xl sm:text-2xl font-serif italic text-white/40">{AXIOM_PHRASES[currentAxiomIndex]}</span>
                  </div>
               </div>
               <div className="h-[2px] w-full bg-white/5 rounded-full overflow-hidden">
                  <div className="h-full bg-silk-gold/40 animate-[drift_3s_linear_infinite]" style={{ width: '45%' }}></div>
               </div>
            </div>
          ) : (
            <div className={`text-2xl sm:text-4xl md:text-5xl lg:text-6xl leading-[1.6] break-words whitespace-pre-wrap ${m.role === Role.assistant ? 'font-serif italic text-ivory/95 selection:bg-silk-gold/40' : 'font-sans text-ivory/70'}`}>
              {m.text}
            </div>
          )}
          
          {m.groundingSources && m.groundingSources.length > 0 && <GroundingNode sources={m.groundingSources} />}

          {m.attachments && m.attachments.length > 0 && (
            <div className="mt-16 grid grid-cols-1 md:grid-cols-2 gap-10">
              {m.attachments.map((at, i) => (
                <div key={i} className="rounded-[40px] overflow-hidden border border-white/5 shadow-2xl relative group bg-black/40 shimmer">
                  {at.type === 'image' && <img src={at.data} className="w-full h-auto grayscale-50 group-hover:grayscale-0 transition-all duration-1000 scale-100 group-hover:scale-105" loading="lazy" />}
                  {at.type === 'video' && <video src={at.uri || at.data} controls className="w-full h-auto" />}
                  <div className="absolute bottom-6 left-6 px-4 py-2 bg-black/60 backdrop-blur-xl border border-white/10 rounded-full text-[10px] font-black uppercase tracking-widest text-silk-gold opacity-0 group-hover:opacity-100 transition-opacity">
                    {at.name}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLiveActive, setIsLiveActive] = useState(false);
  const [showReview, setShowReview] = useState(false);
  const [vibe, setVibe] = useState<SovereignVibe>('Classic');
  const [showVibeDial, setShowVibeDial] = useState(false);
  const [showWhitePaper, setShowWhitePaper] = useState(false);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [volume, setVolume] = useState(0);
  const [currentAxiomIndex, setCurrentAxiomIndex] = useState(0);
  
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const sessionPromiseRef = useRef<Promise<any> | null>(null);
  const audioContextsRef = useRef<{ in?: AudioContext, out?: AudioContext, nextStartTime: number }>({ nextStartTime: 0 });

  const scrollToBottom = (instant = false) => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: instant ? 'auto' : 'smooth' });
    }
  };

  useEffect(() => {
    let interval: number;
    if (isLoading) {
      interval = window.setInterval(() => {
        setCurrentAxiomIndex(prev => (prev + 1) % AXIOM_PHRASES.length);
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [isLoading]);

  useEffect(() => scrollToBottom(), [messages, isLoading]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []) as File[];
    files.forEach(file => {
      const reader = new FileReader();
      reader.onload = (event) => {
        setAttachments(prev => [...prev, {
          name: file.name,
          mimeType: file.type,
          type: file.type.startsWith('image/') ? 'image' : file.type.startsWith('video/') ? 'video' : 'audio',
          data: event.target?.result as string
        }]);
      };
      reader.readAsDataURL(file);
    });
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleSendMessage = async () => {
    if (!inputText.trim() && attachments.length === 0) return;
    
    const currentInput = inputText;
    const currentAttachments = [...attachments];
    
    const userMsg: Message = { 
      id: Date.now().toString(), 
      role: Role.user, 
      text: currentInput, 
      attachments: currentAttachments, 
      timestamp: new Date() 
    };
    
    setMessages(prev => [...prev, userMsg]);
    setInputText('');
    setAttachments([]);
    setIsLoading(true);
    
    const aiMsgId = (Date.now() + 1).toString();
    const aiMsgPlaceholder: Message = { 
      id: aiMsgId, 
      role: Role.assistant, 
      text: "", 
      isThinking: true, 
      timestamp: new Date(),
      modelTier: 'Pro' 
    };
    setMessages(prev => [...prev, aiMsgPlaceholder]);
    
    try {
      const stream = gemini.unifiedExchange(currentInput, messages, currentAttachments, vibe);
      for await (const chunk of stream) {
        setMessages(prev => prev.map(m => m.id === aiMsgId ? { 
          ...m, 
          text: chunk.text, 
          attachments: chunk.attachments, 
          groundingSources: chunk.groundingSources,
          isThinking: !chunk.isDone,
          modelTier: chunk.tier as any,
          verified: chunk.verified
        } : m));
      }
    } catch (err) { 
      setMessages(prev => prev.map(m => m.id === aiMsgId ? { ...m, text: "Gafara dai, an samu kuskure. A sake gwadawa.", isThinking: false } : m));
    } finally { 
      setIsLoading(false); 
    }
  };

  const toggleLiveVoice = async () => {
    if (isLiveActive) {
      if (sessionPromiseRef.current) (await sessionPromiseRef.current).close();
      setIsLiveActive(false);
      setVolume(0);
      return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        if (!audioContextsRef.current.in) audioContextsRef.current.in = new AudioContext({ sampleRate: 16000 });
        if (!audioContextsRef.current.out) audioContextsRef.current.out = new AudioContext({ sampleRate: 24000 });
        
        const inputCtx = audioContextsRef.current.in!;
        const outputCtx = audioContextsRef.current.out!;

        sessionPromiseRef.current = gemini.connectLive({
          onopen: () => {
            setIsLiveActive(true);
            const source = inputCtx.createMediaStreamSource(stream);
            const scriptProcessor = inputCtx.createScriptProcessor(4096, 1, 1);
            scriptProcessor.onaudioprocess = (e) => {
              const inputData = e.inputBuffer.getChannelData(0);
              let sum = 0;
              for (let i = 0; i < inputData.length; i++) sum += inputData[i] * inputData[i];
              setVolume(Math.sqrt(sum / inputData.length));
              sessionPromiseRef.current?.then(s => s.sendRealtimeInput({ media: createBlob(inputData) }));
            };
            source.connect(scriptProcessor);
            scriptProcessor.connect(inputCtx.destination);
          },
          onmessage: async (msg: any) => {
            const base64 = msg.serverContent?.modelTurn?.parts[0]?.inlineData?.data;
            if (base64) {
              const buffer = await decodeAudioData(decode(base64), outputCtx, 24000, 1);
              const source = outputCtx.createBufferSource();
              source.buffer = buffer;
              source.connect(outputCtx.destination);
              audioContextsRef.current.nextStartTime = Math.max(outputCtx.currentTime, audioContextsRef.current.nextStartTime);
              source.start(audioContextsRef.current.nextStartTime);
              audioContextsRef.current.nextStartTime += buffer.duration;
            }
          },
          onclose: () => setIsLiveActive(false),
          onerror: () => setIsLiveActive(false)
        });
    } catch (e) {
        console.error("Mic Access Denied", e);
    }
  };

  return (
    <div className="h-full flex flex-col relative bg-obsidian text-ivory selection:bg-silk-gold/30 font-sans overflow-hidden">
      
      {isLiveActive && (
        <div className="fixed inset-0 pointer-events-none flex items-center justify-center z-0">
          <div className="w-[120vw] h-[120vw] bg-silk-gold opacity-[0.03] rounded-full blur-[200px] sm:blur-[400px] animate-pulse" style={{ transform: `scale(${1 + volume * 4})` }} />
        </div>
      )}

      {/* Modern High-End Header */}
      <header className="fixed top-0 w-full z-50 px-6 sm:px-16 py-8 sm:py-16 flex justify-between items-center bg-gradient-to-b from-obsidian via-obsidian/60 to-transparent backdrop-blur-md">
        <div className="flex items-center gap-6 sm:gap-14 group cursor-pointer" onClick={() => setShowReview(true)}>
          <ArewaLogo size={60} className="sm:w-24 sm:h-24" active={isLoading || isLiveActive} />
          <div className="flex flex-col">
            <h1 className="font-serif italic text-4xl sm:text-7xl text-silk-gold tracking-tighter leading-none">Vertex Sovereign</h1>
            <div className="flex items-center gap-3 mt-2">
              <span className="w-2 h-2 rounded-full bg-silk-gold animate-glow"></span>
              <span className="text-[10px] sm:text-[14px] text-ivory/30 uppercase tracking-[0.8em] font-black italic">Nexus-7 Core Architecture</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-6 sm:gap-10">
           <button 
             onClick={() => setShowVibeDial(!showVibeDial)}
             className="px-8 py-4 rounded-full border border-silk-gold/20 text-[11px] sm:text-[14px] font-black uppercase tracking-widest text-silk-gold hover:bg-silk-gold/10 transition-all shadow-[0_20px_50px_rgba(0,0,0,1)] backdrop-blur-3xl"
           >
             Protocol: {vibe}
           </button>
           {showVibeDial && (
              <div className="absolute top-32 right-16 bg-obsidian/95 border border-silk-gold/20 rounded-[40px] p-4 shadow-[0_60px_120px_rgba(0,0,0,1)] z-[100] animate-reveal backdrop-blur-2xl">
                {(['Classic', 'Royal', 'Cyberpunk', 'Academic'] as SovereignVibe[]).map(v => (
                  <button key={v} onClick={() => { setVibe(v); setShowVibeDial(false); }} className={`w-full text-left px-12 py-6 rounded-3xl text-[12px] uppercase tracking-widest transition-all ${vibe === v ? 'bg-silk-gold/20 text-silk-gold font-bold' : 'text-white/40 hover:text-white hover:bg-white/5'}`}>{v}</button>
                ))}
              </div>
           )}
           <button onClick={() => setShowReview(true)} className="p-6 rounded-full bg-silk-gold/5 text-silk-gold border border-silk-gold/10 hover:bg-silk-gold/20 transition-all shadow-xl">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 21a9 9 0 100-18 9 9 0 000 18z" strokeWidth="1.5"/><path d="M12 8v4l3 3" strokeWidth="2" strokeLinecap="round"/></svg>
           </button>
           <button 
             onClick={() => setShowWhitePaper(true)} 
             className="px-8 py-4 rounded-full bg-white/5 border border-white/10 text-[11px] sm:text-[14px] font-black uppercase tracking-widest text-silk-gold hover:bg-silk-gold/10 transition-all shadow-xl backdrop-blur-3xl flex items-center gap-4"
           >
             <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" strokeWidth="2" strokeLinecap="round"/></svg>
             White Paper
           </button>
        </div>
      </header>

      {/* Conversation Thread */}
      <main ref={scrollRef} className="flex-1 overflow-y-auto px-6 sm:px-16 pt-56 sm:pt-72 pb-80 sm:pb-96 no-scrollbar z-10">
        <div className="max-w-[1400px] mx-auto space-y-32">
          {messages.length === 0 && (
            <div className="h-[65vh] flex flex-col items-center justify-center text-center space-y-24 animate-reveal">
              <h2 className="text-[14rem] sm:text-[28rem] font-serif italic text-silk-gold/5 leading-none select-none tracking-tighter filter blur-[1px]">Arewa</h2>
              <div className="space-y-8">
                <p className="max-w-4xl text-4xl sm:text-7xl text-ivory/25 font-serif italic leading-tight tracking-tighter">Barka da zuwa cibiyar <span className="text-silk-gold/40">Nexus-7</span>. Ingantaccen harshe, martabar al'ada, da zurfin tunani.</p>
                <div className="h-[1px] w-32 bg-silk-gold/30 mx-auto"></div>
              </div>
            </div>
          )}
          {messages.map((m) => (
            <MessageItem key={m.id} m={m} currentAxiomIndex={currentAxiomIndex} />
          ))}
        </div>
      </main>

      {/* Floating Control Console */}
      <footer className="fixed bottom-0 w-full z-50 p-10 sm:p-20 bg-gradient-to-t from-obsidian via-obsidian/98 to-transparent">
        <div className="max-w-[1400px] mx-auto space-y-12">
          
          {(isLiveActive || volume > 0.02) && <div className="h-40 sm:h-72"><Waveform active={isLiveActive} volume={volume} /></div>}

          {attachments.length > 0 && (
            <div className="flex gap-10 px-12 overflow-x-auto no-scrollbar py-8">
               {attachments.map((at, i) => (
                 <div key={i} className="flex-none w-32 h-32 sm:w-48 sm:h-48 rounded-[40px] bg-white/5 border border-white/10 p-2 relative shadow-2xl transition-transform hover:scale-110">
                    <img src={at.data} className="w-full h-full object-cover rounded-[32px]" />
                    <button onClick={() => setAttachments(prev => prev.filter((_, idx) => idx !== i))} className="absolute -top-5 -right-5 bg-red-600/90 backdrop-blur-2xl rounded-full p-3 shadow-2xl hover:scale-125 transition-transform"><svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M6 18L18 6M6 6l12 12" strokeWidth="4"/></svg></button>
                 </div>
               ))}
            </div>
          )}

          <div className="bg-deep-paper/98 backdrop-blur-[60px] rounded-[80px] sm:rounded-[200px] p-6 sm:p-10 border border-silk-gold/20 flex items-center gap-10 shadow-[0_80px_200px_-50px_rgba(0,0,0,1)]">
            <button onClick={() => fileInputRef.current?.click()} className="p-8 sm:p-16 rounded-full text-silk-gold hover:bg-white/5 transition-all"><svg className="w-12 h-12 sm:w-20 sm:h-20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 4v16m8-8H4" strokeWidth="2"/></svg></button>
            <textarea 
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(); } }}
              placeholder="Shigar da umarninka anan..."
              rows={1}
              className="flex-1 bg-transparent py-8 sm:py-16 text-4xl sm:text-8xl focus:outline-none placeholder:text-white/5 font-serif italic resize-none no-scrollbar text-ivory/95"
            />
            <div className="flex items-center gap-6 pr-12">
              <button onClick={toggleLiveVoice} className={`p-8 sm:p-16 rounded-full transition-all ${isLiveActive ? 'bg-red-600 text-white shadow-[0_0_80px_rgba(220,38,38,0.6)] animate-pulse' : 'text-silk-gold hover:bg-white/5'}`}><svg className="w-12 h-12 sm:w-20 sm:h-20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" strokeWidth="3"/></svg></button>
              <button onClick={handleSendMessage} className="p-10 sm:p-20 bg-silk-gold text-obsidian rounded-full shadow-2xl hover:scale-105 active:scale-95 transition-all"><svg className="w-12 h-12 sm:w-20 sm:h-20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7" strokeWidth="4"/></svg></button>
            </div>
          </div>
        </div>
      </footer>
      <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" multiple />
      {showReview && <NeuralReview onClose={() => setShowReview(false)} onOpenWhitePaper={() => setShowWhitePaper(true)} />}
      {showWhitePaper && <WhitePaper onClose={() => setShowWhitePaper(false)} />}
    </div>
  );
};

export default App;
