
import React, { Suspense, lazy } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import App from './App.tsx';
import { ErrorBoundary } from './components/ErrorBoundary.tsx';
import { LazyFallback } from './components/LazyFallback.tsx';

// Regular chat users never visit /admin -- keep the whole admin surface
// (login form, review dashboards, analytics) out of the bundle everyone
// else downloads.
const AdminLogin = lazy(() => import('./components/AdminLogin.tsx').then(m => ({ default: m.AdminLogin })));
const AdminPanel = lazy(() => import('./components/AdminPanel.tsx').then(m => ({ default: m.AdminPanel })));

// Same reasoning as AdminLogin/AdminPanel above -- most chat users never
// follow the /listen link, so keep the MOS listening-test page out of the
// bundle everyone else downloads.
const MosListen = lazy(() => import('./components/MosListen.tsx').then(m => ({ default: m.MosListen })));

const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(
    <React.StrictMode>
      <ErrorBoundary>
        <BrowserRouter>
          <Suspense fallback={<LazyFallback />}>
            <Routes>
              <Route path="/admin/login" element={<AdminLogin />} />
              <Route path="/admin" element={<AdminPanel />} />
              <Route path="/listen" element={<MosListen />} />
              <Route path="/*" element={<App />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
      </ErrorBoundary>
    </React.StrictMode>
  );
} else {
  console.error("Critical Failure: Root mount point not found.");
}


// Register Murya Sovereign PWA Service Worker
if (typeof window !== 'undefined' && 'serviceWorker' in navigator && process.env.NODE_ENV === 'production') {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch((err) => {
      console.warn('Murya PWA SW registration failed:', err);
    });
  });
}
