import { useState } from 'react';
import { ToastItem } from '../components/Toast.tsx';

/** On-brand replacement for window.alert() — see components/Toast.tsx. */
export function useToasts() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const showToast = (message: string, variant: ToastItem['variant'] = 'error') => {
    setToasts(prev => [...prev, { id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, message, variant }]);
  };

  const dismissToast = (id: string) => setToasts(prev => prev.filter(t => t.id !== id));

  return { toasts, showToast, dismissToast };
}
