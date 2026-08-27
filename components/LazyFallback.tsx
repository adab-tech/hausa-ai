import React from 'react';
import { Loader2 } from 'lucide-react';

/** Suspense fallback for lazy-loaded full-screen overlays (NeuralReview,
 * WhitePaper, DocumentTool, etc.) -- matches their own fixed inset-0
 * obsidian surface so there's no flash of blank/white while the chunk
 * downloads. */
export const LazyFallback: React.FC = () => (
  <div className="fixed inset-0 z-[60] bg-dyn-bg-primary/95 backdrop-blur-xl flex items-center justify-center">
    <Loader2 className="w-6 h-6 text-dyn-accent animate-spin" />
  </div>
);
