import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useToasts } from '../useToasts.ts';

describe('useToasts', () => {
  it('starts empty', () => {
    const { result } = renderHook(() => useToasts());
    expect(result.current.toasts).toEqual([]);
  });

  it('showToast appends a toast with a default error variant', () => {
    const { result } = renderHook(() => useToasts());
    act(() => result.current.showToast('Gafara dai'));
    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].message).toBe('Gafara dai');
    expect(result.current.toasts[0].variant).toBe('error');
  });

  it('showToast honors an explicit variant', () => {
    const { result } = renderHook(() => useToasts());
    act(() => result.current.showToast('Saved', 'info'));
    expect(result.current.toasts[0].variant).toBe('info');
  });

  it('multiple toasts get distinct ids so React keys never collide', () => {
    const { result } = renderHook(() => useToasts());
    act(() => {
      result.current.showToast('first');
      result.current.showToast('second');
    });
    expect(result.current.toasts).toHaveLength(2);
    expect(result.current.toasts[0].id).not.toBe(result.current.toasts[1].id);
  });

  it('dismissToast removes only the matching toast', () => {
    const { result } = renderHook(() => useToasts());
    act(() => {
      result.current.showToast('keep me');
      result.current.showToast('remove me');
    });
    const idToRemove = result.current.toasts[1].id;
    act(() => result.current.dismissToast(idToRemove));
    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].message).toBe('keep me');
  });
});
