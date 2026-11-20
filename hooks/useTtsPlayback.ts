/// <reference types="vite/client" />

import { useRef, useState } from 'react';
import { gemini } from '../services/localService.ts';
import { chunkTextForTts } from '../utils/textChunking.ts';

// Comfortably under the backend's /api/tts max_length=2000 (see
// backend/routers/audio.py's tts_endpoint) -- leaves margin rather than
// chunking right up against the server's own limit.
const MAX_CHUNK_CHARS = 1800;
const RELAY_CHUNK_CHARS = 300;
const BUSY_RETRY_DELAYS_MS = [1000, 2000, 4000, 4000];

function waitToRetry(delay: number, signal: AbortSignal): Promise<void> {
  if (signal.aborted) return Promise.resolve();
  return new Promise((resolve) => {
    const finish = () => {
      clearTimeout(timer);
      signal.removeEventListener('abort', finish);
      resolve();
    };
    const timer = setTimeout(finish, delay);
    signal.addEventListener('abort', finish, { once: true });
  });
}

async function loadVoiceChunk(text: string, speakerId: number, signal: AbortSignal): Promise<Blob | null> {
  try {
    for (let attempt = 0; !signal.aborted; attempt++) {
      const response = await fetch('/api/voice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, speaker_id: speakerId }),
        signal,
      });
      if (response.ok) return await response.blob();
      const delay = BUSY_RETRY_DELAYS_MS[attempt];
      if (response.status !== 503 || delay === undefined) return null;
      const retryAfter = Number(response.headers.get('Retry-After') ?? 0) * 1000;
      if (retryAfter > 4000) return null;
      await waitToRetry(Math.max(delay, retryAfter || 0), signal);
    }
  } catch {
    // Fetch may reject after a user stops playback. The caller checks its signal.
  }
  return null;
}

/** Plays a message's text as speech via the TTS endpoint, tracking which
 * message (if any) is currently playing so the UI can show the right
 * play/pause state per bubble.
 *
 * A reply longer than the server's per-request text cap (routine for a
 * detailed explanation) is split into several requests and played
 * back-to-back through the same <audio> element, rather than sent as one
 * request the server now rejects outright -- see chunkTextForTts's own
 * comment for why that cap exists. */
export function useTtsPlayback(speakerId: number | null, showToast: (message: string) => void) {
  const [playingSpeechId, setPlayingSpeechId] = useState<string | null>(null);
  const ttsAudioRef = useRef<HTMLAudioElement | null>(null);
  const playbackRequestRef = useRef<AbortController | null>(null);
  const nextChunkRef = useRef<Promise<Blob | null> | null>(null);
  const blobUrlRef = useRef<string | null>(null);
  const useVoiceRelay = import.meta.env.VITE_MURYA_VOICE_RELAY === "1"
    && (speakerId === null || speakerId === 0 || speakerId === 6);
  // The chunk queue for whichever message is currently playing. Cleared on
  // every stop/pause/switch so a stale onended from a just-superseded
  // <audio> element can never advance a queue that no longer belongs to
  // the active playback.
  const ttsQueueRef = useRef<string[]>([]);
  // Mirrors playingSpeechId but updates SYNCHRONOUSLY (a ref, not React
  // state, which batches). Two click events landing before a re-render
  // both see the SAME pre-update playingSpeechId if the gate below reads
  // that state value directly -- both then take the "start fresh" branch,
  // each independently resetting the queue and restarting chunk 0, so the
  // user hears the opening of a long reply loop back to its own start and
  // never reaches the rest of it. Found live: a single real click on
  // murya.ng produced two separate chunk-0 Audio instances back-to-back.
  // handlePlaySpeech reads this ref instead, so the second call in the
  // same tick correctly sees "already active" and stops instead of
  // restarting.
  const activeMessageIdRef = useRef<string | null>(null);

  const stopCurrent = () => {
    playbackRequestRef.current?.abort();
    playbackRequestRef.current = null;
    nextChunkRef.current = null;
    if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
    blobUrlRef.current = null;
    if (ttsAudioRef.current) {
      ttsAudioRef.current.onended = null;
      ttsAudioRef.current.onerror = null;
      ttsAudioRef.current.pause();
      ttsAudioRef.current = null;
    }
    ttsQueueRef.current = [];
  };

  const finish = () => {
    activeMessageIdRef.current = null;
    setPlayingSpeechId(null);
  };

  const playChunkAt = async (index: number) => {
    const chunks = ttsQueueRef.current;
    if (index >= chunks.length) {
      stopCurrent();
      finish();
      return;
    }

    const request = playbackRequestRef.current;
    let url: string;
    if (request) {
      const pending = nextChunkRef.current ?? loadVoiceChunk(chunks[index], speakerId ?? 6, request.signal);
      nextChunkRef.current = null;
      const blob = await pending;
      if (request.signal.aborted) return;
      if (!blob?.size) {
        stopCurrent();
        finish();
        showToast("Gafara dai, an samu kuskure wajen sauti.");
        return;
      }
      if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
      url = URL.createObjectURL(blob);
      blobUrlRef.current = url;
    } else {
      url = gemini.getTtsUrl(chunks[index], speakerId);
    }
    const audio = new Audio(url);
    ttsAudioRef.current = audio;

    const failPlayback = (error: unknown) => {
      if (ttsAudioRef.current !== audio) return;
      console.error("TTS playback failed", error);
      stopCurrent();
      finish();
      showToast("Gafara dai, an samu kuskure wajen sauti.");
    };
    audio.onended = () => {
      if (ttsAudioRef.current !== audio) return;
      audio.onended = null;
      audio.onerror = null;
      ttsAudioRef.current = null;
      void playChunkAt(index + 1);
    };
    audio.onerror = failPlayback;
    audio.play().then(() => {
      // Synthesize one chunk ahead while the current audio plays.
      if (request && !request.signal.aborted && ttsAudioRef.current === audio && index + 1 < chunks.length) {
        nextChunkRef.current = loadVoiceChunk(chunks[index + 1], speakerId ?? 6, request.signal);
      }
    }).catch(failPlayback);
  };

  const handlePlaySpeech = (text: string, messageId: string, normalized?: string) => {
    // Prefer the orthography-normalized text (ɓɗƙƴ instead of b'/d'/k'/y'
    // apostrophe fallbacks) so playback doesn't mispronounce hooked
    // consonants as their plain counterparts. The backend also normalizes
    // internally now, but doing it here too means this still helps even if
    // some future caller bypasses that.
    text = normalized || text;
    if (activeMessageIdRef.current === messageId) {
      stopCurrent();
      finish();
      return;
    }

    stopCurrent();
    activeMessageIdRef.current = messageId;
    if (useVoiceRelay) playbackRequestRef.current = new AbortController();
    ttsQueueRef.current = chunkTextForTts(text, useVoiceRelay ? RELAY_CHUNK_CHARS : MAX_CHUNK_CHARS);
    setPlayingSpeechId(messageId);
    void playChunkAt(0);
  };

  return { playingSpeechId, handlePlaySpeech };
}
