import { useRef, useState } from 'react';
import { gemini } from '../services/localService.ts';

/** Plays a message's text as speech via the TTS endpoint, tracking which
 * message (if any) is currently playing so the UI can show the right
 * play/pause state per bubble. */
export function useTtsPlayback(speakerId: number | null, showToast: (message: string) => void) {
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
    // audio.play() returns a Promise that can reject on its own (blocked
    // autoplay policy, AbortError from a fast pause/replace, etc.) -- a
    // failure mode distinct from the element's onerror event below, and
    // previously unhandled: the UI would silently stay "playing" with no
    // sound and no indication anything went wrong.
    audio.play().catch((err) => {
      console.error("TTS playback failed to start", err);
      setPlayingSpeechId(null);
      alert("Gafara dai, an samu kuskure wajen sauti.");
    });
    audio.onended = () => {
      setPlayingSpeechId(null);
    };
    audio.onerror = (e) => {
      console.error("TTS playback error", e);
      setPlayingSpeechId(null);
      showToast("Gafara dai, an samu kuskure wajen sauti.");
    };
  };

  return { playingSpeechId, handlePlaySpeech };
}
