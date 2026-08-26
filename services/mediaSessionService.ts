/**
 * mediaSessionService.ts — Integrates Murya 24kHz TTS with hardware media session controls
 *
 * Displays active speaker (Malama Asabe or Malam Garba) and transcription text
 * on Android and iOS lock screen notification bars.
 */

export function setupMediaSession(options: {
  title: string;
  speaker: string;
  audioElement?: HTMLAudioElement;
  onPlay?: () => void;
  onPause?: () => void;
}) {
  if (typeof window === 'undefined' || !('mediaSession' in navigator)) return;

  try {
    navigator.mediaSession.metadata = new MediaMetadata({
      title: options.title.slice(0, 60) + (options.title.length > 60 ? '...' : ''),
      artist: options.speaker.includes('Asabe') ? 'Murya AI · Malama Asabe' : 'Murya AI · Malam Garba',
      album: 'Murya Sovereign Hausa OS',
      artwork: [
        { src: '/icon-192.svg', sizes: '192x192', type: 'image/svg+xml' },
        { src: '/icon-512.svg', sizes: '512x512', type: 'image/svg+xml' }
      ]
    });

    if (options.onPlay) {
      navigator.mediaSession.setActionHandler('play', options.onPlay);
    }
    if (options.onPause) {
      navigator.mediaSession.setActionHandler('pause', options.onPause);
    }
  } catch (err) {
    console.warn('MediaSession registration warning:', err);
  }
}
