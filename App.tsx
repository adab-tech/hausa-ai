import { OfflineBanner } from './components/OfflineBanner.tsx';
import { InstallPromptBanner } from './components/InstallPromptBanner.tsx';
import React, { useState, useRef, useEffect, useMemo, Suspense, lazy } from 'react';
import { Attachment, SovereignVibe, AddresseeGender } from './types.ts';
import { ArewaLogo } from './components/ArewaLogo.tsx';
import { Waveform } from './components/Waveform.tsx';
import { LazyFallback } from './components/LazyFallback.tsx';
import { Sidebar } from './components/Sidebar.tsx';
import { LiveCallPanel } from './components/LiveCallPanel.tsx';
import { InputConsole } from './components/InputConsole.tsx';
import { MessageItem } from './components/MessageItem.tsx';
import { ToastHost } from './components/Toast.tsx';
import { Menu } from 'lucide-react';
import { useToasts } from './hooks/useToasts.ts';
import { useChat } from './hooks/useChat.ts';
import { useLiveVoice } from './hooks/useLiveVoice.ts';
import { useTtsPlayback } from './hooks/useTtsPlayback.ts';

// Lazy-loaded: these are full-screen overlays gated behind a boolean toggle,
// not part of the initial chat view -- most visitors never open any of
// them, so they shouldn't ship in the first-load bundle. Each also pulls in
// its own dependents (NeuralReview alone brings PronunciationReview +
// VisitorAnalytics), which is exactly the weight this keeps out of the
// critical path.
const NeuralReview = lazy(() => import('./components/NeuralReview.tsx').then(m => ({ default: m.NeuralReview })));
const WhitePaper = lazy(() => import('./components/WhitePaper.tsx').then(m => ({ default: m.WhitePaper })));
const DocumentTool = lazy(() => import('./components/DocumentTool.tsx').then(m => ({ default: m.DocumentTool })));
const ContributePronunciation = lazy(() => import('./components/ContributePronunciation.tsx').then(m => ({ default: m.ContributePronunciation })));
const ContributeQA = lazy(() => import('./components/ContributeQA.tsx').then(m => ({ default: m.ContributeQA })));
const DictionarySearch = lazy(() => import('./components/DictionarySearch.tsx').then(m => ({ default: m.DictionarySearch })));

const App: React.FC = () => {
  const [inputText, setInputText] = useState('');
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
  // Default to speaker 6 (Malama Asabe) — chosen 2026-08-23 after listening
  // to all 8 voice samples. Voice 0 (Malam Garba) is the other featured
  // voice (see components/Sidebar.tsx's FEATURED_VOICES), rather than the
  // ambiguous null "baseline" path.
  const [speakerId, setSpeakerId] = useState<number | null>(6);
  const [showSpeakerDial, setShowSpeakerDial] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const { toasts, showToast, dismissToast } = useToasts();

  const {
    messages, setMessages, visibleMessages, isLoading, currentAxiomIndex,
    feedbacks, handleSendMessage: sendMessage, handleFeedback,
  } = useChat(vibe, addresseeGender, learningMode);

  const { isLiveActive, volume, callDuration, voiceStatus, toggleLiveVoice } =
    useLiveVoice(speakerId, addresseeGender, setMessages, showToast);

  const { playingSpeechId, handlePlaySpeech } = useTtsPlayback(speakerId, showToast);

  const handleSendMessage = () => sendMessage(inputText, attachments, () => {
    setInputText('');
    setAttachments([]);
  });

  const scrollRef = useRef<HTMLDivElement>(null);
  const scrollToBottom = (instant = false) => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: instant ? 'auto' : 'smooth' });
    }
  };
  useEffect(() => scrollToBottom(), [messages, isLoading]);

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
            {visibleMessages.length === 0 && (
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
            {visibleMessages.map((m) => (
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

      {/* Modals overlay -- each lazy chunk gets its own Suspense boundary
          since they're independently toggleable, not mutually exclusive
          (WhitePaper can open from inside NeuralReview). */}
      {showReview && (
        <Suspense fallback={<LazyFallback />}>
          <NeuralReview
            onClose={() => setShowReview(false)}
            onOpenWhitePaper={() => setShowWhitePaper(true)}
          />
        </Suspense>
      )}
      {showWhitePaper && (
        <Suspense fallback={<LazyFallback />}>
          <WhitePaper
            onClose={() => setShowWhitePaper(false)}
          />
        </Suspense>
      )}
      {showDocumentTool && (
        <Suspense fallback={<LazyFallback />}>
          <DocumentTool onClose={() => setShowDocumentTool(false)} />
        </Suspense>
      )}
      {showContribute && (
        <Suspense fallback={<LazyFallback />}>
          <ContributePronunciation onClose={() => setShowContribute(false)} />
        </Suspense>
      )}
      {showContributeQA && (
        <Suspense fallback={<LazyFallback />}>
          <ContributeQA onClose={() => setShowContributeQA(false)} />
        </Suspense>
      )}
      {showDictionary && (
        <Suspense fallback={<LazyFallback />}>
          <DictionarySearch onClose={() => setShowDictionary(false)} />
        </Suspense>
      )}

      <OfflineBanner />
      <div className="fixed top-3 inset-x-0 z-40 flex justify-center px-4 pointer-events-none [&>*]:pointer-events-auto">
        <InstallPromptBanner />
      </div>

      <ToastHost toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
};

export default App;
