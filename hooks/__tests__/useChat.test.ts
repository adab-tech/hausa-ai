import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

vi.mock('../../services/localService.ts', () => ({
  gemini: {
    recordVisit: vi.fn().mockResolvedValue(undefined),
    recordFeedback: vi.fn().mockResolvedValue(undefined),
    unifiedExchange: vi.fn(),
  },
}));
vi.mock('../../services/learningService.ts', () => ({
  learning: {
    getMemoryPrompt: vi.fn().mockReturnValue(''),
    recordFeedback: vi.fn(),
  },
}));

import { useChat } from '../useChat.ts';
import { gemini } from '../../services/localService.ts';
import { learning } from '../../services/learningService.ts';
import { Role } from '../../types.ts';

// Builds the same shape unifiedExchange actually yields (see chatService.ts),
// as an async generator, so the hook's `for await` loop drives real code.
async function* fakeStream(chunks: { text: string; isDone: boolean }[]) {
  for (const c of chunks) {
    yield { text: c.text, attachments: [], groundingSources: [], isDone: c.isDone, tier: 'Pro', verified: false };
  }
}

describe('useChat', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('records exactly one visit on mount', () => {
    renderHook(() => useChat('Classic', 'unspecified', false));
    expect(gemini.recordVisit).toHaveBeenCalledTimes(1);
  });

  it('handleSendMessage appends the user message immediately, then streams the assistant reply in', async () => {
    (gemini.unifiedExchange as ReturnType<typeof vi.fn>).mockReturnValue(
      fakeStream([
        { text: 'Ana...', isDone: false },
        { text: 'Barka da zuwa.', isDone: true },
      ])
    );
    const { result } = renderHook(() => useChat('Classic', 'unspecified', false));
    const onSent = vi.fn();

    await act(async () => {
      await result.current.handleSendMessage('sannu', [], onSent);
    });

    expect(onSent).toHaveBeenCalledTimes(1); // clears the input box in the caller
    expect(result.current.isLoading).toBe(false); // finally{} cleared it
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0]).toMatchObject({ role: Role.user, text: 'sannu' });
    expect(result.current.messages[1]).toMatchObject({ role: Role.assistant, text: 'Barka da zuwa.', isThinking: false });
  });

  it('empty input with no attachments is a no-op -- never calls the backend', async () => {
    const { result } = renderHook(() => useChat('Classic', 'unspecified', false));
    const onSent = vi.fn();

    await act(async () => {
      await result.current.handleSendMessage('   ', [], onSent);
    });

    expect(gemini.unifiedExchange).not.toHaveBeenCalled();
    expect(onSent).not.toHaveBeenCalled();
    expect(result.current.messages).toHaveLength(0);
  });

  it('a stream failure replaces the placeholder with the Hausa error message, not a stuck spinner', async () => {
    // Deliberately throws before any yield -- simulates the stream failing
    // immediately (e.g. fetch() itself rejecting), which is exactly the
    // path useChat's catch block exists to handle.
    // eslint-disable-next-line require-yield
    (gemini.unifiedExchange as ReturnType<typeof vi.fn>).mockImplementation(async function* () {
      throw new Error('backend unreachable');
    });
    const { result } = renderHook(() => useChat('Classic', 'unspecified', false));

    await act(async () => {
      await result.current.handleSendMessage('sannu', [], vi.fn());
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.messages[1].text).toBe('Gafara dai, an samu kuskure. A sake gwadawa.');
    expect(result.current.messages[1].isThinking).toBe(false);
  });

  it('handleFeedback records once and ignores a second vote on the same message', () => {
    const { result } = renderHook(() => useChat('Classic', 'unspecified', false));
    act(() => {
      result.current.setMessages([
        { id: 'm1', role: Role.assistant, text: 'reply', timestamp: new Date() },
      ]);
    });

    act(() => result.current.handleFeedback('m1', 'up'));
    act(() => result.current.handleFeedback('m1', 'down')); // should be a no-op now

    expect(result.current.feedbacks['m1']).toBe('up');
    expect(gemini.recordFeedback).toHaveBeenCalledTimes(1);
    expect(learning.recordFeedback).toHaveBeenCalledTimes(1);
  });

  it('visibleMessages hides live-voice turns but keeps them in messages for context', () => {
    const { result } = renderHook(() => useChat('Classic', 'unspecified', false));
    act(() => {
      result.current.setMessages([
        { id: 'm1', role: Role.user, text: 'typed', timestamp: new Date() },
        { id: 'm2', role: Role.assistant, text: 'spoken reply', timestamp: new Date(), fromLiveVoice: true },
      ]);
    });

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.visibleMessages).toHaveLength(1);
    expect(result.current.visibleMessages[0].id).toBe('m1');
  });
});
