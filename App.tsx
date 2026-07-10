import React, { useState, useRef, useEffect, useMemo } from 'react';
import { gemini } from './services/localService.ts';
import { learning } from './services/learningService.ts';
import { Message, Role, Attachment, SovereignVibe, AddresseeGender } from './types.ts';
import { ArewaLogo } from './components/ArewaLogo.tsx';
import { Waveform } from './components/Waveform.tsx';
import { NeuralReview } from './components/NeuralReview.tsx';
import { WhitePaper } from './components/WhitePaper.tsx';
import { Sidebar } from './components/Sidebar.tsx';
import { LiveCallPanel } from './components/LiveCallPanel.tsx';
import { InputConsole } from './components/InputConsole.tsx';
import { MessageItem, AXIOM_PHRASES } from './components/MessageItem.tsx';
import { decodeAudioData, decode, createBlob } from './utils/audio.ts';
import { Menu, Compass } from 'lucide-react';

const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLiveActive, setIsLiveActive] = useState(false);
  const [showReview, setShowReview] = useState(false);
  const [vibe, setVibe] = useState<SovereignVibe>('Classic');
  const [showVibeDial, setShowVibeDial] = useState(false);
  const [addresseeGender, setAddresseeGenderState] = useState<AddresseeGender>(() => {
    const stored = localStorage.getItem('hausa_ai_addressee_gender');
    return stored === 'masculine' || stored === 'feminine' ? stored : 'unspecified';
  });
  const setAddresseeGender = (g: AddresseeGender) => {
    setAddresseeGenderState(g);
    localStorage.setItem('hausa_ai_addressee_gender', g);
  };
  const [showAddresseeDial, setShowAddresseeDial] = useState(false);
  const [showWhitePaper, setShowWhitePaper] = useState(false);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [volume, setVolume] = useState(0);
  const [currentAxiomIndex, setCurrentAxiomIndex] = useState(0);
  const [speakerId, setSpeakerId] = useState<number | null>(null);
  const [showSpeakerDial, setShowSpeakerDial] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [callDuration, setCallDuration] = useState(0);
  const [voiceStatus, setVoiceStatus] = useState<'idle' | 'requesting_permission' | 'connecting' | 'connected' | 'error'>('idle');
  const [liveTranscripts, setLiveTranscripts] = useState<Array<{ role: 'user' | 'assistant'; text: string }>>([]);
  const [feedbacks, setFeedbacks] = useState<Record<string, 'up' | 'down'>>({});
  const [playingSpeechId, setPlayingSpeechId] = useState<string | null>(null);
  const ttsAudioRef = useRef<HTMLAudioElement | null>(null);

  const handlePlaySpeech = (text: string, messageId: string) => {
    if (playingSpeechId === messageId) {
      if (ttsAudioRef.current) {
        ttsAudioRef.current.pause();
        setPlayingSpeechId(null);
      }
      return;
    }

    if (ttsAudioRef.current) {
      ttsAudioRef.current.pause();
    }

    const url = gemini.getTtsUrl(text, speakerId);
    const audio = new Audio(url);
    ttsAudioRef.current = audio;
    setPlayingSpeechId(messageId);
    audio.play();
    audio.onended = () => {
      setPlayingSpeechId(null);
    };
    audio.onerror = (e) => {
      console.error("TTS playback error", e);
      setPlayingSpeechId(null);
      alert("Gafara dai, an samu kuskure wajen sauti.");
    };
  };

  const scrollRef = useRef<HTMLDivElement>(null);
  const sessionPromiseRef = useRef<Promise<any> | null>(null);
  const audioContextsRef = useRef<{ in?: AudioContext, out?: AudioContext, nextStartTime: number }>({ nextStartTime: 0 });
  const timerRef = useRef<NodeJS.Timeout | null>(null);

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

  // Handle call timer when live voice is active
  useEffect(() => {
    if (isLiveActive) {
      setCallDuration(0);
      timerRef.current = setInterval(() => {
        setCallDuration(prev => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      setCallDuration(0);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isLiveActive]);

  useEffect(() => scrollToBottom(), [messages, isLoading]);

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
      const stream = gemini.unifiedExchange(currentInput, messages, currentAttachments, vibe, addresseeGender);
      for await (const chunk of stream) {
        setMessages(prev => prev.map(m => m.id === aiMsgId ? {
          ...m,
          text: chunk.text,
          attachments: chunk.attachments,
          groundingSources: chunk.groundingSources,
          isThinking: !chunk.isDone,
          modelTier: chunk.tier as any,
          verified: chunk.verified,
          normalized: chunk.normalized,
          toneMapped: chunk.toneMapped
        } : m));
      }
    } catch (err) {
      setMessages(prev => prev.map(m => m.id === aiMsgId ? { ...m, text: "Gafara dai, an samu kuskure. A sake gwadawa.", isThinking: false } : m));
    } finally {
      setIsLoading(false);
    }
  };

  const handleFeedback = (messageId: string, feedback: 'up' | 'down', correction?: string) => {
    if (feedbacks[messageId]) return;
    setFeedbacks(prev => ({ ...prev, [messageId]: feedback }));
    const msg = messages.find(m => m.id === messageId);
    if (msg) {
      learning.recordFeedback(messageId, feedback, msg.text);
      gemini.recordFeedback(messageId, feedback, msg.text, correction);
    }
  };

  const toggleLiveVoice = async () => {
    if (isLiveActive) {
      if (sessionPromiseRef.current) (await sessionPromiseRef.current).close();
      setIsLiveActive(false);
      setVolume(0);
      setVoiceStatus('idle');
      return;
    }

    // Microphone requires a secure context (HTTPS or localhost) and a browser
    // that exposes getUserMedia. Over plain http on a network IP, or inside a
    // sandboxed iframe, navigator.mediaDevices is undefined — surface that
    // precisely instead of a misleading "permission denied".
    if (!navigator.mediaDevices?.getUserMedia) {
      setVoiceStatus('error');
      alert(
        "Ba a iya buɗe makirufo ba. Ana buƙatar amintacciyar hanya (HTTPS ko 'localhost') " +
        "kuma browser mai goyon bayan makirufo.\n\n" +
        "(Live voice needs a secure HTTPS or localhost page — it won't work over plain http " +
        "or inside a restricted preview frame. It will work on the deployed https site.)"
      );
      return;
    }

    try {
        setVoiceStatus('requesting_permission');
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        setVoiceStatus('connecting');
        setLiveTranscripts([]);

        if (!audioContextsRef.current.in) audioContextsRef.current.in = new AudioContext({ sampleRate: 16000 });
        if (!audioContextsRef.current.out) audioContextsRef.current.out = new AudioContext({ sampleRate: 24000 });

        const inputCtx = audioContextsRef.current.in!;
        const outputCtx = audioContextsRef.current.out!;

        sessionPromiseRef.current = gemini.connectLive(speakerId, {
          onopen: () => {
            setIsLiveActive(true);
            setVoiceStatus('connected');
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
            if (msg.text) {
              setLiveTranscripts(prev => [...prev, { role: msg.isUser ? 'user' : 'assistant', text: msg.text }]);
              setMessages(prev => [...prev, {
                id: Date.now().toString(),
                role: msg.isUser ? Role.user : Role.assistant,
                text: msg.text,
                timestamp: new Date(),
                normalized: msg.normalized,
                toneMapped: msg.tone_mapped
              }]);
            }
          },
          onclose: () => {
            setIsLiveActive(false);
            setVoiceStatus('idle');
          },
          onerror: () => {
            setIsLiveActive(false);
            setVoiceStatus('error');
          }
        }, addresseeGender);
    } catch (e: any) {
        const name = e?.name || '';
        console.error("Live voice mic error:", name, e);
        setVoiceStatus('error');
        setIsLiveActive(false);
        if (name === 'NotAllowedError' || name === 'SecurityError' || name === 'PermissionDeniedError') {
          alert("Ba a ba da izinin makirufo ba. Da fatan za a ba da izini a saitunan browser sannan a sake gwadawa.\n(Microphone permission was denied — allow it in your browser and try again.)");
        } else if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
          alert("Ba a sami makirufo ba a na'urarka.\n(No microphone was found on this device.)");
        } else if (name === 'NotReadableError' || name === 'TrackStartError') {
          alert("Makirufo yana amfani da wata manhaja a yanzu. A rufe ta sannan a sake gwadawa.\n(The microphone is in use by another application.)");
        } else {
          alert("An samu matsala wajen buɗe makirufo: " + (e?.message || name || 'unknown') + "\n(Could not start the microphone.)");
        }
    }
  };

  const clearChat = () => {
    if (window.confirm("Shin kana son goge dukkan hirar nan?")) {
      setMessages([]);
    }
  };

  const dynamicVibeClass = useMemo(() => {
    return `vibe-${vibe.toLowerCase()}`;
  }, [vibe]);

  return (
    <div className={`h-full w-full flex ${dynamicVibeClass} bg-dyn-bg-primary text-dyn-text-primary selection:bg-dyn-accent/30 font-sans overflow-hidden transition-all duration-700`}>

      {/* Background decoration grid */}
      <div className="zana-grid" />

      {/* Floating pulse light when live call is active */}
      {isLiveActive && (
        <div className="fixed inset-0 pointer-events-none flex items-center justify-center z-0">
          <div className="w-[110vw] h-[110vw] bg-dyn-accent opacity-[0.03] rounded-full blur-[150px] sm:blur-[300px] animate-pulse-slow" style={{ transform: `scale(${1 + volume * 2})` }} />
        </div>
      )}

      <Sidebar
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
        isLoading={isLoading}
        isLiveActive={isLiveActive}
        vibe={vibe}
        setVibe={setVibe}
        showVibeDial={showVibeDial}
        setShowVibeDial={setShowVibeDial}
        speakerId={speakerId}
        setSpeakerId={setSpeakerId}
        showSpeakerDial={showSpeakerDial}
        setShowSpeakerDial={setShowSpeakerDial}
        addresseeGender={addresseeGender}
        setAddresseeGender={setAddresseeGender}
        showAddresseeDial={showAddresseeDial}
        setShowAddresseeDial={setShowAddresseeDial}
        onOpenReview={() => setShowReview(true)}
        onOpenWhitePaper={() => setShowWhitePaper(true)}
        onClearChat={clearChat}
        hasMessages={messages.length > 0}
      />

      {/* ── MAIN CONTENT AREA ── */}
      <div className="flex-1 flex flex-col relative min-w-0 z-10">

        {isLiveActive && (
          <LiveCallPanel
            voiceStatus={voiceStatus}
            callDuration={callDuration}
            liveTranscripts={liveTranscripts}
            onHangup={toggleLiveVoice}
          />
        )}

        {/* Global Floating Header (Mobile and Top Bar) */}
        <header className="px-6 py-4 flex justify-between items-center bg-dyn-bg-primary/40 backdrop-blur-md border-b border-dyn-border/30 md:border-b-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              aria-label="Buɗe menu (Open menu)"
              className="md:hidden p-2 text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5 rounded-xl border border-dyn-border/40"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3 md:hidden">
              <ArewaLogo size={32} active={isLoading || isLiveActive} />
              <h2 className="font-serif italic text-xl text-dyn-accent tracking-tighter">Hausa AI</h2>
            </div>
          </div>

          {/* Secondary stats preview */}
          <div className="flex items-center gap-4 text-dyn-text-muted text-[10px] font-mono select-none">
            <div className="hidden sm:flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
              <span>Server: 127.0.0.1</span>
            </div>
            <span className="hidden sm:inline">|</span>
            <div className="flex items-center gap-1 font-sans font-bold uppercase tracking-wider text-dyn-accent">
              <Compass className="w-3.5 h-3.5" />
              <span>{vibe} Mode</span>
            </div>
          </div>
        </header>

        {/* Conversation Thread */}
        <main ref={scrollRef} className="flex-1 overflow-y-auto px-4 sm:px-10 py-6 space-y-16 no-scrollbar relative z-10">
          <div className="max-w-[900px] mx-auto space-y-12">
            {messages.length === 0 && (
              <div className="h-[60vh] flex flex-col items-center justify-center text-center space-y-8 animate-reveal">
                <div className="flex justify-center select-none"><ArewaLogo size={100} active={isLoading || isLiveActive} watermark /></div>
                <div className="space-y-4 max-w-2xl">
                  <h2 className="text-4xl sm:text-6xl font-serif italic text-dyn-accent leading-none tracking-tight">Barka da zuwa cibiyar Hausa AI</h2>
                  <p className="text-dyn-text-secondary text-base sm:text-xl font-serif italic leading-relaxed">
                    Ingantaccen harshe, martabar al'ada, da zurfin tunanin ilimi. Rubuta umarni a kasa don fara tattaunawa ko danna alamar makirufo domin sautin murya na kai-tsaye.
                  </p>
                  <div className="h-[1px] w-24 bg-dyn-accent/30 mx-auto mt-6"></div>
                </div>
              </div>
            )}
            {messages.map((m) => (
              <MessageItem
                key={m.id}
                m={m}
                currentAxiomIndex={currentAxiomIndex}
                onFeedback={handleFeedback}
                feedback={feedbacks[m.id]}
                onPlaySpeech={handlePlaySpeech}
                playingSpeechId={playingSpeechId}
              />
            ))}
          </div>
        </main>

        {/* Voice calling visualizer bar */}
        {isLiveActive && volume > 0.01 && (
          <div className="h-16 w-full z-20 border-t border-dyn-border/20 bg-dyn-bg-primary/20 backdrop-blur-sm animate-reveal overflow-hidden">
            <Waveform active={isLiveActive} volume={volume} />
          </div>
        )}

        <InputConsole
          inputText={inputText}
          setInputText={setInputText}
          attachments={attachments}
          setAttachments={setAttachments}
          isLoading={isLoading}
          isLiveActive={isLiveActive}
          onSendMessage={handleSendMessage}
          onToggleLiveVoice={toggleLiveVoice}
        />
      </div>

      {/* Modals overlay */}
      {showReview && (
        <NeuralReview
          onClose={() => setShowReview(false)}
          onOpenWhitePaper={() => setShowWhitePaper(true)}
        />
      )}
      {showWhitePaper && (
        <WhitePaper
          onClose={() => setShowWhitePaper(false)}
        />
      )}
    </div>
  );
};

export default App;
