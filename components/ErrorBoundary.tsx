import React from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

interface Props {
  children: React.ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * Top-level render-error catch. Without this, any uncaught error thrown
 * during render (a bad API payload shape, a null ref, etc.) white-screens
 * the whole app for the user with no way back except manually reloading.
 * React only supports this via a class component -- no hook equivalent.
 */
export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('Murya render error:', error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="fixed inset-0 z-[300] flex items-center justify-center bg-dyn-bg px-6">
          <div className="manuscript-bubble rounded-2xl px-7 py-8 max-w-sm w-full flex flex-col items-center text-center gap-4 border-l-[3px] border-l-red-500/70">
            <AlertTriangle className="w-6 h-6 text-red-400" />
            <div className="space-y-1.5">
              <p className="text-dyn-text-primary font-medium">Wani kuskure ya faru</p>
              <p className="text-sm text-dyn-text-muted leading-relaxed">Something went wrong. Reloading usually fixes it.</p>
            </div>
            <button
              onClick={() => window.location.reload()}
              className="mt-1 inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-dyn-accent text-dyn-bg text-sm font-medium hover:opacity-90 transition-opacity"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Sake ɗorawa (Reload)
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
