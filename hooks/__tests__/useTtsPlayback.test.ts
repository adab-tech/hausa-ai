import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

vi.mock('../../services/localService.ts', () => ({
  gemini: { getTtsUrl: vi.fn().mockReturnValue('https://api.murya.ng/api/tts?text=x') },
}));

import { useTtsPlayback } from '../useTtsPlayback.ts';

// happy-dom's <audio> doesn't implement real playback -- stub the bits the
// hook actually touches (play/pause/onended/onerror) so this test drives
// the hook's own state machine, not a real media pipeline.
class FakeAudio {
  onended: (() => void) | null = null;
  onerror: ((e: unknown) => void) | null = null;
  play = vi.fn().mockResolvedValue(undefined);
  pause = vi.fn();
}

describe('useTtsPlayback', () => {
  let showToast: (message: string) => void;
  let lastAudio: FakeAudio;

  beforeEach(() => {
    showToast = vi.fn();
    // mockImplementation must be a real function, not an arrow function --
    // arrow functions can never be called with `new`, and the hook does
    // `new Audio(url)`.
    vi.stubGlobal(
      'Audio',
      vi.fn().mockImplementation(function () {
        lastAudio = new FakeAudio();
        return lastAudio;
      })
    );
  });

  it('starts a new message playing and clears playingSpeechId when it ends', async () => {
    const { result } = renderHook(() => useTtsPlayback(6, showToast));

    await act(async () => {
      result.current.handlePlaySpeech('sannu', 'm1');
    });
    expect(result.current.playingSpeechId).toBe('m1');

    act(() => lastAudio.onended?.());
    expect(result.current.playingSpeechId).toBeNull();
  });

  it('clicking the same message again pauses it instead of restarting', async () => {
    const { result } = renderHook(() => useTtsPlayback(6, showToast));

    await act(async () => {
      result.current.handlePlaySpeech('sannu', 'm1');
    });
    const firstAudio = lastAudio;

    await act(async () => {
      result.current.handlePlaySpeech('sannu', 'm1');
    });

    expect(firstAudio.pause).toHaveBeenCalledTimes(1);
    expect(result.current.playingSpeechId).toBeNull();
  });

  it('switching to a different message pauses the previous one first', async () => {
    const { result } = renderHook(() => useTtsPlayback(6, showToast));

    await act(async () => {
      result.current.handlePlaySpeech('sannu', 'm1');
    });
    const firstAudio = lastAudio;

    await act(async () => {
      result.current.handlePlaySpeech('yaya kake', 'm2');
    });

    expect(firstAudio.pause).toHaveBeenCalledTimes(1);
    expect(result.current.playingSpeechId).toBe('m2');
  });

  it('an onerror event clears playback state and shows a toast', async () => {
    const { result } = renderHook(() => useTtsPlayback(6, showToast));

    await act(async () => {
      result.current.handlePlaySpeech('sannu', 'm1');
    });
    act(() => lastAudio.onerror?.(new Event('error')));

    expect(result.current.playingSpeechId).toBeNull();
    expect(showToast).toHaveBeenCalledWith('Gafara dai, an samu kuskure wajen sauti.');
  });

  it('prefers the normalized text over the raw text when both are given', async () => {
    const { result } = renderHook(() => useTtsPlayback(6, showToast));
    const { gemini } = await import('../../services/localService.ts');

    await act(async () => {
      result.current.handlePlaySpeech('raw b-text', 'm1', 'normalized ɓ-text');
    });

    expect(gemini.getTtsUrl).toHaveBeenCalledWith('normalized ɓ-text', 6);
  });
});
