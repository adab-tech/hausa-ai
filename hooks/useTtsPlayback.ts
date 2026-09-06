import { useRef, useState } from 'react';
import { gemini } from '../services/localService.ts';
import { chunkTextForTts } from '../utils/textChunking.ts';

// Comfortably under the backend's /api/tts max_length=2000 (see
// backend/routers/audio.py's tts_endpoint) -- leaves margin rather than
// chunking right up against the server's own limit.
const MAX_CHUNK_CHARS = 1800;

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
    if (ttsAudioRef.current) {
      ttsAudioRef.current.onended = null;
      ttsAudioRef.current.onerror = null;
      ttsAudioRef.current.pause();
    }
    ttsQueueRef.current = [];
  };

  const finish = () => {
    activeMessageIdRef.current = null;
    setPlayingSpeechId(null);
  };

  const playChunkAt = (index: number) => {
    const chunks = ttsQueueRef.current;
    if (index >= chunks.length) {
      finish();
      return;
    }

    const url = gemini.getTtsUrl(chunks[index], speakerId);
    const audio = new Audio(url);
    ttsAudioRef.current = audio;

    // audio.play() returns a Promise that can reject on its own (blocked
    // autoplay policy, AbortError from a fast pause/replace, etc.) -- a
    // failure mode distinct from the element's onerror event below, and
    // previously unhandled: the UI would silently stay "playing" with no
    // sound and no indication anything went wrong.
    audio.play().catch((err) => {
      console.error("TTS playback failed to start", err);
      stopCurrent();
      finish();
      alert("Gafara dai, an samu kuskure wajen sauti.");
    });
    audio.onended = () => {
      // Long replies play as several back-to-back chunks -- advance to the
      // next one instead of ending playback just because THIS chunk's
      // audio finished.
      playChunkAt(index + 1);
    };
    audio.onerror = (e) => {
      console.error("TTS playback error", e);
      stopCurrent();
      finish();
      showToast("Gafara dai, an samu kuskure wajen sauti.");
    };
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
    ttsQueueRef.current = chunkTextForTts(text, MAX_CHUNK_CHARS);
    setPlayingSpeechId(messageId);
    playChunkAt(0);
  };

  return { playingSpeechId, handlePlaySpeech };
}
