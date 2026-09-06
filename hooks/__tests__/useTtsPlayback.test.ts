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

  // ---------------------------------------------------------------------
  // Regression: /api/tts caps a single request's text at 2000 chars (see
  // backend/routers/audio.py) after an unbounded request OOM'd production
  // on 2026-09-03. A reply longer than that used to be sent as one request
  // the server now rejects with 422 -- the <audio> element reported that
  // as a plain playback error, i.e. "Saurara fails on longer texts". It's
  // now split into several requests played back-to-back through the same
  // element instead.
  // ---------------------------------------------------------------------
  it('plays a long message as multiple chunks back-to-back, one audio element per chunk', async () => {
    const audios: FakeAudio[] = [];
    vi.stubGlobal(
      'Audio',
      vi.fn().mockImplementation(function () {
        const a = new FakeAudio();
        audios.push(a);
        return a;
      })
    );

    const { result } = renderHook(() => useTtsPlayback(6, showToast));
    // Three sentences, each well under the chunk limit alone but forced
    // into separate chunks by a text long enough overall to need it.
    const longText = 'Kalma. '.repeat(400).trim(); // ~2800 chars, all one "sentence" shape repeated

    await act(async () => {
      result.current.handlePlaySpeech(longText, 'm1');
    });

    expect(result.current.playingSpeechId).toBe('m1');
    expect(audios.length).toBe(1); // only the first chunk has started so far

    // Finishing the first chunk must advance to the next one, not end
    // playback -- and playingSpeechId must stay set throughout.
    act(() => audios[0].onended?.());
    expect(audios.length).toBe(2);
    expect(result.current.playingSpeechId).toBe('m1');

    act(() => audios[1].onended?.());
    // Keep advancing until the queue is exhausted.
    while (result.current.playingSpeechId === 'm1' && audios.length < 20) {
      act(() => audios[audios.length - 1].onended?.());
    }

    expect(result.current.playingSpeechId).toBeNull();
    expect(audios.length).toBeGreaterThan(1);
  });

  it('stopping mid-sequence prevents the next chunk from starting', async () => {
    const audios: FakeAudio[] = [];
    vi.stubGlobal(
      'Audio',
      vi.fn().mockImplementation(function () {
        const a = new FakeAudio();
        audios.push(a);
        return a;
      })
    );

    const { result } = renderHook(() => useTtsPlayback(6, showToast));
    const longText = 'Kalma. '.repeat(400).trim();

    await act(async () => {
      result.current.handlePlaySpeech(longText, 'm1');
    });
    const countAfterStart = audios.length;

    // Click the same message again mid-playback -- stops the whole
    // sequence, not just the current chunk.
    await act(async () => {
      result.current.handlePlaySpeech(longText, 'm1');
    });
    expect(result.current.playingSpeechId).toBeNull();
    expect(audios[0].onended).toBeNull();

    // A late onended firing from the stopped element (a real-world race
    // between pause() and a queued event) must not resurrect playback.
    act(() => audios[0].onended?.());
    expect(audios.length).toBe(countAfterStart);
    expect(result.current.playingSpeechId).toBeNull();
  });
});
