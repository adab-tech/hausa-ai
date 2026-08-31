import React, { useEffect, useRef, useState } from 'react';
import { gemini } from '../services/localService.ts';
import type { MosClip, MosAnswer } from '../services/mosService.ts';
import { Play, Pause, Loader2, Headphones, Check } from 'lucide-react';

const SESSION_SIZE_HINT = 20;
const SCALE_LABELS = ['', 'Bad', 'Poor', 'Fair', 'Good', 'Excellent'];
const REGIONS = ['Nigeria', 'Niger', 'Ghana', 'Cameroon', 'Chad', 'Jamhuriyar Afirka ta Tsakiya (CAR)', 'Diaspora', 'Ban ambata ba (prefer not to say)'];

function shuffle<T>(arr: T[]): T[] {
  const copy = [...arr];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

/** Public: Murya's MOS (naturalness) listening test. Blind, randomized,
 * anonymous. Results feed the admin "TTS Evaluation" dashboard — see
 * backend/mos_store.py. Nothing here approves anything for training by
 * itself; that's a separate, explicit admin decision. */
export const MosListen: React.FC = () => {
  const [phase, setPhase] = useState<'intro' | 'loading' | 'rating' | 'submitting' | 'done' | 'error'>('intro');
  const [region, setRegion] = useState('');
  const [nativeSpeaker, setNativeSpeaker] = useState(false);
  const [clips, setClips] = useState<MosClip[]>([]);
  const [idx, setIdx] = useState(0);
  const [answers, setAnswers] = useState<MosAnswer[]>([]);
  const [score, setScore] = useState<number | null>(null);
  const [intel, setIntel] = useState<'yes' | 'partial' | 'no' | null>(null);
  const [hasPlayed, setHasPlayed] = useState(false);
  const [replays, setReplays] = useState(0);
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const sessionIdRef = useRef<string>('');

  useEffect(() => {
    return () => { audioRef.current?.pause(); };
  }, []);

  const start = async () => {
    setPhase('loading');
    const session = await gemini.getMosSession();
    if (!session || session.length === 0) {
      setPhase('error');
      return;
    }
    sessionIdRef.current = (globalThis.crypto?.randomUUID?.() ?? String(Date.now()));
    setClips(shuffle(session));
    setIdx(0);
    setAnswers([]);
    resetClipState();
    setPhase('rating');
  };

  const resetClipState = () => {
    setScore(null);
    setIntel(null);
    setHasPlayed(false);
    setReplays(0);
    setPlaying(false);
    audioRef.current?.pause();
    audioRef.current = null;
  };

  const play = () => {
    const clip = clips[idx];
    if (!clip) return;
    if (audioRef.current) {
      if (playing) { audioRef.current.pause(); setPlaying(false); return; }
      audioRef.current.play(); setPlaying(true);
      if (hasPlayed) setReplays((r) => r + 1);
      setHasPlayed(true);
      return;
    }
    const a = new Audio(gemini.mosAudioUrl(clip.clip_id));
    audioRef.current = a;
    a.addEventListener('ended', () => setPlaying(false));
    a.play();
    setPlaying(true);
    setHasPlayed(true);
  };

  const next = () => {
    const clip = clips[idx];
    if (!clip || score === null || intel === null) return;
    const answer: MosAnswer = {
      clip_id: clip.clip_id, condition: clip.condition, voice: clip.voice,
      sentence_id: clip.sentence_id, score, intelligible: intel, replays,
    };
    const nextAnswers = [...answers, answer];
    setAnswers(nextAnswers);
    if (idx < clips.length - 1) {
      setIdx(idx + 1);
      resetClipState();
    } else {
      finish(nextAnswers);
    }
  };

  const finish = async (finalAnswers: MosAnswer[]) => {
    setPhase('submitting');
    const ok = await gemini.submitMosSession(sessionIdRef.current, finalAnswers, region || null, nativeSpeaker);
    setPhase(ok ? 'done' : 'error');
  };

  const ready = hasPlayed && score !== null && intel !== null;

  return (
    <div className="min-h-screen w-full bg-dyn-bg-primary text-dyn-text-primary font-sans flex flex-col">
      <header className="px-4 sm:px-10 py-6 border-b border-dyn-border/40 flex items-center gap-3">
        <Headphones className="w-5 h-5 text-dyn-accent shrink-0" />
        <div className="min-w-0">
          <h1 className="font-serif italic text-xl leading-none">Gwajin Murya</h1>
          <p className="text-[9px] uppercase tracking-[0.2em] sm:tracking-[0.3em] text-dyn-text-muted mt-1 truncate">Listening test</p>
        </div>
      </header>

      <main className="flex-1 flex items-start justify-center px-4 sm:px-6 py-10 min-w-0">
        <div className="w-full max-w-xl min-w-0">

          {phase === 'intro' && (
            <div className="space-y-6">
              <p className="text-sm text-dyn-text-secondary leading-relaxed">
                Za ka ji gajerun sauti — wasu na haƙiƙa muryar ɗan Adam, wasu Murya ce ta faɗa —
                sannan ka kimanta yadda suke kama da magana ta gaskiya. Kimanin mintuna 5.
                (You'll hear short clips — some real human speech, some Murya — and rate how
                natural each one sounds. About 5 minutes.)
              </p>

              <div className="space-y-2">
                <label className="text-[10px] uppercase tracking-widest text-dyn-text-muted font-bold">Ina kake? (Where are you based — optional)</label>
                <select value={region} onChange={(e) => setRegion(e.target.value)}
                  className="w-full rounded-xl bg-dyn-bg-tertiary/50 border border-dyn-border px-4 py-3 text-sm text-dyn-text-primary focus:outline-none">
                  <option value="">Zaɓi ɗaya (select one)</option>
                  {REGIONS.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>

              <div className="flex items-start gap-3">
                <input id="native" type="checkbox" checked={nativeSpeaker} onChange={(e) => setNativeSpeaker(e.target.checked)}
                  className="mt-1 w-[18px] h-[18px] accent-dyn-accent" />
                <label htmlFor="native" className="text-sm text-dyn-text-primary">Ni mai magana da Hausa ne, ko na san ta sosai. (I am a native or fluent Hausa speaker.)</label>
              </div>

              <p className="text-[11px] text-dyn-text-muted/70 italic">
                Ba a tattara suna ba. Ba za ka san wanne tsari ya yi kowanne sauti ba yayin kimantawa.
                (Anonymous. Clips are unlabeled — you won't know which system made which clip.)
              </p>

              <button onClick={start} className="w-full flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-dyn-accent text-dyn-bg-primary text-sm font-bold uppercase tracking-wider">
                Fara Gwaji (Begin listening test)
              </button>
            </div>
          )}

          {phase === 'loading' && (
            <div className="flex justify-center py-16"><Loader2 className="w-6 h-6 animate-spin text-dyn-accent" /></div>
          )}

          {phase === 'error' && (
            <div className="text-center py-16 space-y-3">
              <p className="text-sm text-dyn-text-secondary">An samu matsala wajen ɗauko gwajin. A sake gwadawa daga baya. (Couldn't load the test — please try again later.)</p>
              <button onClick={() => setPhase('intro')} className="px-5 py-2.5 rounded-full border border-dyn-border text-dyn-text-secondary text-xs uppercase tracking-wider hover:text-dyn-text-primary">Sake gwadawa (Retry)</button>
            </div>
          )}

          {phase === 'rating' && clips[idx] && (
            <div className="space-y-8">
              <div>
                <p className="text-[11px] font-mono text-dyn-text-muted mb-2">Sauti {idx + 1} na {clips.length} (Clip {idx + 1} of {clips.length})</p>
                <div className="h-[3px] bg-dyn-bg-tertiary rounded-full overflow-hidden">
                  <div className="h-full bg-dyn-accent transition-all" style={{ width: `${(idx / clips.length) * 100}%` }} />
                </div>
              </div>

              <div className="rounded-2xl border border-dyn-border bg-dyn-bg-tertiary/20 py-12 flex flex-col items-center gap-4">
                <p className="text-[10px] uppercase tracking-widest text-dyn-text-muted">Sauti mara suna · a saurara da belun kunne (unlabeled clip · headphones recommended)</p>
                <button onClick={play} aria-label={playing ? 'Pause' : 'Play'}
                  className={`w-24 h-24 rounded-full flex items-center justify-center transition-transform hover:scale-105 active:scale-95 ${playing ? 'bg-dyn-accent' : 'bg-dyn-accent/90'}`}>
                  {playing ? <Pause className="w-8 h-8 text-dyn-bg-primary" /> : <Play className="w-8 h-8 text-dyn-bg-primary ml-1" />}
                </button>
                <p className="text-xs text-dyn-text-muted">{hasPlayed ? 'A sake danna don sake ji (tap to replay)' : 'Danna don ji (tap to play)'}</p>
              </div>

              <div className="space-y-3">
                <p className="text-[10px] uppercase tracking-widest text-dyn-text-muted font-bold">Yaya yake da kamar magana ta gaskiya? (How natural did this sound?)</p>
                <div className="grid grid-cols-5 gap-2">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <button key={n} onClick={() => setScore(n)}
                      className={`flex flex-col items-center gap-1 py-3 rounded-xl border text-center ${score === n ? 'border-dyn-accent bg-dyn-accent/15' : 'border-dyn-border hover:border-dyn-accent/40'}`}>
                      <span className="font-serif text-xl">{n}</span>
                      <span className="text-[10px] text-dyn-text-muted">{SCALE_LABELS[n]}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <p className="text-[10px] uppercase tracking-widest text-dyn-text-muted font-bold">Ka fahimci kowace kalma? (Could you understand every word?)</p>
                <div className="flex gap-2 flex-wrap">
                  {([
                    { v: 'yes', label: 'Eh, duka (Yes, all of it)' },
                    { v: 'partial', label: 'Yawancinsu (Mostly)' },
                    { v: 'no', label: 'A\'a / ba a bayyana ba (No / unclear)' },
                  ] as const).map((o) => (
                    <button key={o.v} onClick={() => setIntel(o.v)}
                      className={`px-4 py-2 rounded-full text-xs border ${intel === o.v ? 'bg-dyn-accent text-dyn-bg-primary border-dyn-accent' : 'border-dyn-border text-dyn-text-secondary hover:text-dyn-text-primary'}`}>
                      {o.label}
                    </button>
                  ))}
                </div>
              </div>

              <button onClick={next} disabled={!ready}
                className="w-full flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-dyn-accent text-dyn-bg-primary text-sm font-bold uppercase tracking-wider disabled:opacity-30 disabled:cursor-not-allowed">
                {idx === clips.length - 1 ? 'Gama (Finish)' : 'Na gaba (Next clip)'}
              </button>
            </div>
          )}

          {phase === 'submitting' && (
            <div className="flex justify-center py-16"><Loader2 className="w-6 h-6 animate-spin text-dyn-accent" /></div>
          )}

          {phase === 'done' && (
            <div className="text-center py-16 space-y-4">
              <div className="w-14 h-14 rounded-full bg-emerald-500/20 border border-emerald-500/50 flex items-center justify-center mx-auto"><Check className="w-7 h-7 text-emerald-400" /></div>
              <h3 className="font-serif italic text-2xl">Na gode! (Thank you)</h3>
              <p className="text-sm text-dyn-text-secondary max-w-sm mx-auto">Ka kimanta sauti {answers.length}. Wannan yana taimaka wa Murya ta inganta. (You rated {answers.length} clips — this directly helps improve Murya's voice.)</p>
              <button onClick={() => setPhase('intro')} className="mt-2 px-6 py-2.5 rounded-full border border-dyn-border text-dyn-text-secondary text-xs uppercase tracking-wider hover:text-dyn-text-primary">Sake yin gwaji (Take it again)</button>
            </div>
          )}
        </div>
      </main>

      <footer className="px-6 sm:px-10 py-5 text-center text-[11px] text-dyn-text-muted/70">
        Wani ɓangare na <a href="https://murya.ng" className="underline hover:text-dyn-text-secondary">Murya</a> — kimanin sauti {SESSION_SIZE_HINT} kowace zama.
      </footer>
    </div>
  );
};
