import React, { useState, useRef, useEffect, useMemo } from 'react';
import { gemini, BACKEND_URL } from './services/localService.ts';
import { learning } from './services/learningService.ts';
import { Message, Role, Attachment, SovereignVibe, AddresseeGender } from './types.ts';
import { ArewaLogo } from './components/ArewaLogo.tsx';
import { Waveform } from './components/Waveform.tsx';
import { NeuralReview } from './components/NeuralReview.tsx';
import { WhitePaper } from './components/WhitePaper.tsx';
import { DocumentTool } from './components/DocumentTool.tsx';
import { ContributePronunciation } from './components/ContributePronunciation.tsx';
import { ContributeQA } from './components/ContributeQA.tsx';
import { DictionarySearch } from './components/DictionarySearch.tsx';
import { Sidebar } from './components/Sidebar.tsx';
import { LiveCallPanel } from './components/LiveCallPanel.tsx';
import { InputConsole } from './components/InputConsole.tsx';
import { MessageItem, AXIOM_PHRASES } from './components/MessageItem.tsx';
import { decodeAudioData, decode, createBlob, makeAudioContext, resampleLinear } from './utils/audio.ts';
import { Menu } from 'lucide-react';

const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLiveActive, setIsLiveActive] = useState(false);
  const [showReview, setShowReview] = useState(false);
  // Always Classic — the client-facing app doesn't expose a protocol/vibe
  // switcher (removed 2026-08-23: English mode names like "Royal"/
  // "Cyberpunk" didn't fit a Hausa-first product). The type/CSS machinery
  // stays in place for AdminPanel.tsx and possible future internal use.
  const [vibe] = useState<SovereignVibe>('Classic');
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
  // Learning Mode: turns Murya into Malamin Hausa (a patient Hausa tutor).
  const [learningMode, setLearningMode] = useState(false);
  const [showDocumentTool, setShowDocumentTool] = useState(false);
  const [showContribute, setShowContribute] = useState(false);
  const [showContributeQA, setShowContributeQA] = useState(false);
  const [showDictionary, setShowDictionary] = useState(false);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [volume, setVolume] = useState(0);
  const [currentAxiomIndex, setCurrentAxiomIndex] = useState(0);
  // Default to speaker 6 (Malama Asabe) — chosen 2026-08-23 after listening
  // to all 8 voice samples. Voice 0 (Malam Garba) is the other featured
  // voice (see components/Sidebar.tsx's FEATURED_VOICES), rather than the
  // ambiguous null "baseline" path.
  const [speakerId, setSpeakerId] = useState<number | null>(6);
  const [showSpeakerDial, setShowSpeakerDial] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [callDuration, setCallDuration] = useState(0);
  const [voiceStatus, setVoiceStatus] = useState<'idle' | 'requesting_permission' | 'connecting' | 'connected' | 'error'>('idle');
  const [liveTranscripts, setLiveTranscripts] = useState<Array<{ role: 'user' | 'assistant'; text: string }>>([]);
  const [feedbacks, setFeedbacks] = useState<Record<string, 'up' | 'down'>>({});
  const [playingSpeechId, setPlayingSpeechId] = useState<string | null>(null);
  const ttsAudioRef = useRef<HTMLAudioElement | null>(null);

  const handlePlaySpeech = (text: string, messageId: string, normalized?: string) => {
    // Prefer the orthography-normalized text (ɓɗƙƴ instead of b'/d'/k'/y'
    // apostrophe fallbacks) so playback doesn't mispronounce hooked
    // consonants as their plain counterparts. The backend also normalizes
    // internally now, but doing it here too means this still helps even if
    // some future caller bypasses that.
    text = normalized || text;
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
  // Pending "assistant finished speaking" notification for the live-voice
  // server-side echo backstop (see setAssistantSpeaking in localService.ts).
  // Re-armed on every TTS chunk so it always fires `tail` seconds after the
  // LAST scheduled chunk of the current reply finishes, not the first.
  const assistantSpeakingOffTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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

  // Record one privacy-preserving visit per app load (no IP; geography by
  // browser timezone, uniqueness by the anonymous contributor id). Fire once.
  useEffect(() => { gemini.recordVisit(); }, []);

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
      const stream = gemini.unifiedExchange(currentInput, messages, currentAttachments, vibe, addresseeGender, learningMode ? 'tutor' : 'assistant');
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
      if (assistantSpeakingOffTimerRef.current) {
        clearTimeout(assistantSpeakingOffTimerRef.current);
        assistantSpeakingOffTimerRef.current = null;
      }
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
        // echoCancellation is essential: without it the mic picks up the
        // assistant's own TTS from the speakers and the model ends up
        // transcribing and answering itself. (Belt: the half-duplex gate in
        // onaudioprocess below; braces: this constraint.)
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
        });
        setVoiceStatus('connecting');
        setLiveTranscripts([]);

        // Robust context creation. The 16000 for input is only a HINT — older
        // Safari and some Android WebViews throw on (or silently ignore) a
        // forced sampleRate, so makeAudioContext falls back to the device
        // default and we resample mic frames to 16 kHz ourselves below. The
        // output context deliberately uses the default rate: decodeAudioData
        // builds AudioBuffers tagged 24000 explicitly, and WebAudio resamples
        // buffers to the context rate automatically at playback.
        if (!audioContextsRef.current.in) audioContextsRef.current.in = makeAudioContext(16000);
        if (!audioContextsRef.current.out) audioContextsRef.current.out = makeAudioContext();

        const inputCtx = audioContextsRef.current.in!;
        const outputCtx = audioContextsRef.current.out!;

        // iOS Safari frequently leaves AudioContexts "suspended" even after a
        // user gesture — playback then never happens and out.currentTime stays
        // frozen, which would also jam the half-duplex mic gate below. We are
        // still inside the tap handler here, so resume() is permitted; await
        // it so scheduling starts from a running clock.
        try {
          await Promise.all([inputCtx.resume(), outputCtx.resume()]);
        } catch {
          // Non-fatal: some browsers reject resume() on an already-running
          // context; state is re-checked before each playback below.
        }

        sessionPromiseRef.current = gemini.connectLive(speakerId, {
          onopen: () => {
            setIsLiveActive(true);
            setVoiceStatus('connected');
            const source = inputCtx.createMediaStreamSource(stream);
            // ScriptProcessor is deprecated (future migration: AudioWorklet
            // with a ScriptProcessor fallback), but it still works everywhere
            // today and keeps the volume meter + half-duplex gate logic simple.
            // It is connected to destination below because some browsers never
            // fire onaudioprocess otherwise (its output is silence).
            const scriptProcessor = inputCtx.createScriptProcessor(4096, 1, 1);
            // The REAL capture rate — browsers that ignored the 16000 hint
            // (Safari, many WebViews) typically run at 44100/48000 here.
            const captureRate = inputCtx.sampleRate;
            scriptProcessor.onaudioprocess = (e) => {
              const inputData = e.inputBuffer.getChannelData(0);
              let sum = 0;
              for (let i = 0; i < inputData.length; i++) sum += inputData[i] * inputData[i];
              setVolume(Math.sqrt(sum / inputData.length));
              // Half-duplex gate: while the assistant's reply is still playing
              // (nextStartTime marks the scheduled END of queued TTS audio),
              // plus a short tail for speaker-to-mic latency, do NOT stream mic
              // frames — otherwise the model hears and answers itself even
              // with echoCancellation on (speakerphones/low-end devices leak).
              //
              // CRITICAL: only gate when the output context is actually RUNNING
              // and some TTS has been scheduled (nextStartTime > 0). iOS Safari
              // routinely leaves the output context 'suspended', which FREEZES
              // out.currentTime at 0 — without these guards the gate would then
              // read "still playing" forever and mute the mic for the whole call
              // (the model never hears you: "connects but silent"). When the
              // context isn't running there is no TTS coming out anyway, so it
              // is safe to send the mic.
              const out = audioContextsRef.current.out;
              if (
                out && out.state === 'running' &&
                audioContextsRef.current.nextStartTime > 0 &&
                out.currentTime < audioContextsRef.current.nextStartTime + 0.4
              ) return;
              // The server expects 16 kHz mono PCM-16. If the context runs at
              // the hardware rate (hint ignored), downsample this frame first —
              // otherwise 48 kHz audio gets interpreted as 16 kHz and the
              // user's voice arrives ~3x slow/garbled at the ASR. Encode the
              // blob synchronously: the browser may recycle inputData before
              // the session promise resolves (resampleLinear always copies).
              const frame16k = resampleLinear(inputData, captureRate, 16000);
              const media = createBlob(frame16k);
              sessionPromiseRef.current?.then(s => s.sendRealtimeInput({ media }));
            };
            source.connect(scriptProcessor);
            scriptProcessor.connect(inputCtx.destination);
          },
          onmessage: async (msg: any) => {
            const base64 = msg.serverContent?.modelTurn?.parts[0]?.inlineData?.data;
            if (base64) {
              // iOS Safari can re-suspend the context (tab switch, route
              // change, interruption); scheduling on a suspended context is
              // silent and freezes currentTime, jamming the mic gate above.
              if (outputCtx.state === 'suspended') {
                try { await outputCtx.resume(); } catch { /* re-checked next chunk */ }
              }
              // 24000 here is the SERVER's PCM rate, not the context rate —
              // WebAudio resamples the buffer to outputCtx.sampleRate on play.
              const buffer = await decodeAudioData(decode(base64), outputCtx, 24000, 1);
              const source = outputCtx.createBufferSource();
              source.buffer = buffer;
              source.connect(outputCtx.destination);
              audioContextsRef.current.nextStartTime = Math.max(outputCtx.currentTime, audioContextsRef.current.nextStartTime);
              source.start(audioContextsRef.current.nextStartTime);
              audioContextsRef.current.nextStartTime += buffer.duration;

              // Server-side echo backstop: tell the backend the assistant is
              // (still) speaking so it drops any mic audio that leaks past
              // this client's own half-duplex gate above — e.g. the brief
              // scheduling race between a chunk starting to play and the
              // next onaudioprocess callback picking up the new
              // nextStartTime, or echoCancellation simply not being enough
              // on a laptop's built-in speakers. "false" is re-armed on
              // every chunk so it always fires after the LAST queued chunk
              // of this reply (+ the same 0.4s tail as the client gate),
              // not the first.
              sessionPromiseRef.current?.then(s => s.setAssistantSpeaking?.(true));
              if (assistantSpeakingOffTimerRef.current) clearTimeout(assistantSpeakingOffTimerRef.current);
              const offDelayMs = Math.max(0, (audioContextsRef.current.nextStartTime - outputCtx.currentTime + 0.4) * 1000);
              assistantSpeakingOffTimerRef.current = setTimeout(() => {
                sessionPromiseRef.current?.then(s => s.setAssistantSpeaking?.(false));
              }, offDelayMs);
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
            if (assistantSpeakingOffTimerRef.current) {
              clearTimeout(assistantSpeakingOffTimerRef.current);
              assistantSpeakingOffTimerRef.current = null;
            }
            setIsLiveActive(false);
            setVoiceStatus('idle');
          },
          onerror: () => {
            if (assistantSpeakingOffTimerRef.current) {
              clearTimeout(assistantSpeakingOffTimerRef.current);
              assistantSpeakingOffTimerRef.current = null;
            }
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
        speakerId={speakerId}
        setSpeakerId={setSpeakerId}
        showSpeakerDial={showSpeakerDial}
        setShowSpeakerDial={setShowSpeakerDial}
        addresseeGender={addresseeGender}
        setAddresseeGender={setAddresseeGender}
        showAddresseeDial={showAddresseeDial}
        setShowAddresseeDial={setShowAddresseeDial}
        learningMode={learningMode}
        setLearningMode={setLearningMode}
        onOpenDocumentTool={() => setShowDocumentTool(true)}
        onOpenContribute={() => setShowContribute(true)}
        onOpenContributeQA={() => setShowContributeQA(true)}
        onOpenDictionary={() => setShowDictionary(true)}
        onOpenReview={() => setShowReview(true)}
        onOpenWhitePaper={() => setShowWhitePaper(true)}
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
              className="md:hidden p-3 text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5 rounded-xl border border-dyn-border/40"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3 md:hidden">
              <ArewaLogo size={32} active={isLoading || isLiveActive} />
              <h2 className="font-serif italic text-xl text-dyn-accent tracking-tighter">Murya</h2>
            </div>
          </div>

          {/* Secondary stats preview */}
          <div className="flex items-center gap-4 text-dyn-text-muted text-[10px] font-mono select-none">
            <span
              className="text-dyn-accent/80 font-mono uppercase text-[10px] tracking-[0.25em] px-3 py-1.5 border border-dyn-accent/30"
              style={{ clipPath: 'polygon(7px 0, 100% 0, 100% calc(100% - 7px), calc(100% - 7px) 100%, 0 100%, 0 7px)' }}
            >
              Fasahar Hausa
            </span>
          </div>
        </header>

        {/* Conversation Thread */}
        <main ref={scrollRef} className="flex-1 overflow-y-auto px-4 sm:px-10 py-6 space-y-16 no-scrollbar relative z-10">
          <div className="max-w-[900px] mx-auto space-y-12">
            {messages.length === 0 && (
              <div className="h-[60vh] flex flex-col items-center justify-center text-center space-y-8 animate-reveal">
                <div className="flex justify-center select-none"><ArewaLogo size={100} active={isLoading || isLiveActive} watermark /></div>
                <div className="space-y-4 max-w-2xl">
                  <h2 className="text-4xl sm:text-6xl font-serif italic text-dyn-accent leading-none tracking-tight">Barka da zuwa Murya</h2>
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
      {showDocumentTool && (
        <DocumentTool onClose={() => setShowDocumentTool(false)} />
      )}
      {showContribute && (
        <ContributePronunciation onClose={() => setShowContribute(false)} />
      )}
      {showContributeQA && (
        <ContributeQA onClose={() => setShowContributeQA(false)} />
      )}
      {showDictionary && (
        <DictionarySearch onClose={() => setShowDictionary(false)} />
      )}
    </div>
  );
};

export default App;
