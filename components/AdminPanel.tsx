import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { gemini } from '../services/localService.ts';
import { useAdminFetch } from '../hooks/useAdminFetch.ts';
import { ArewaLogo } from './ArewaLogo.tsx';
import { CorrectionsReview } from './CorrectionsReview.tsx';
import { PronunciationReview } from './PronunciationReview.tsx';
import { QAReview } from './QAReview.tsx';
import { VisitorAnalytics } from './VisitorAnalytics.tsx';
import { ChangePasswordDialog } from './ChangePasswordDialog.tsx';
import { LogOut, KeyRound, FileText, Mic, Globe, MessageSquare, History, RefreshCw, Loader2 } from 'lucide-react';

/** ADMIN: read-only trail of every approve/reject/delete/record action across
 * corrections, pronunciation, and Q&A review — see backend/admin_audit_store.py.
 * Minimal by design (single-admin app, see admin_store.py): a plain
 * newest-first table, no filtering UI beyond what the endpoint already
 * supports. This is a safety net for "what did I just do", not a reporting
 * dashboard. */
const AuditLogView: React.FC = () => {
  const { data: items, loading, denied, reload } = useAdminFetch(() => gemini.getAuditLog());

  if (loading && !items) return <div className="flex justify-center py-10"><Loader2 className="w-5 h-5 animate-spin text-dyn-accent" /></div>;
  if (denied || !items) return <p className="text-dyn-text-muted text-sm p-4">An hana shiga. (Admin login required.)</p>;

  const actionColor = (action: string) => {
    if (action === 'delete') return 'text-red-400';
    if (action === 'approved' || action === 'approve' || action === 'create' || action === 'record') return 'text-emerald-400';
    if (action === 'rejected' || action === 'reject') return 'text-amber-400';
    return 'text-dyn-text-secondary';
  };

  return (
    <div className="space-y-4 animate-reveal">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-serif italic text-xl text-dyn-text-primary">Tarihin Aiki</h3>
          <p className="text-[10px] uppercase tracking-widest text-dyn-text-muted">Audit log · every approve/reject/delete across all three review surfaces</p>
        </div>
        <button onClick={reload} className="p-2 rounded-lg text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5" aria-label="Refresh"><RefreshCw className="w-4 h-4" /></button>
      </div>

      {items.length === 0 ? (
        <p className="text-center py-12 text-dyn-text-muted italic text-sm">Babu wani aiki tukuna. (No admin actions recorded yet.)</p>
      ) : (
        <div className="rounded-2xl border border-dyn-border overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-dyn-bg-tertiary/40 text-[9px] uppercase tracking-wider text-dyn-text-muted">
                <th className="p-3">Lokaci (When)</th>
                <th className="p-3">Admin</th>
                <th className="p-3">Aiki (Action)</th>
                <th className="p-3">Sashe (Surface)</th>
                <th className="p-3">Abu (Item)</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id} className="border-t border-dyn-border/30">
                  <td className="p-3 font-mono text-dyn-text-muted whitespace-nowrap">{new Date(row.created_at * 1000).toLocaleString()}</td>
                  <td className="p-3 text-dyn-text-primary">{row.admin}</td>
                  <td className={`p-3 font-bold uppercase ${actionColor(row.action)}`}>{row.action}</td>
                  <td className="p-3 text-dyn-text-secondary capitalize">{row.surface}</td>
                  <td className="p-3 text-dyn-text-secondary truncate max-w-xs" title={row.detail ?? undefined}>
                    {row.target_id ? `#${row.target_id}` : ''}{row.detail ? ` — ${row.detail}` : ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export const AdminPanel: React.FC = () => {
  const navigate = useNavigate();
  const [username, setUsername] = useState<string | null | 'loading'>('loading');
  const [tab, setTab] = useState<'corrections' | 'pronunciation' | 'qa' | 'visitors' | 'audit'>('corrections');
  const [showChangePassword, setShowChangePassword] = useState(false);

  useEffect(() => {
    let cancelled = false;
    gemini.adminMe().then((u) => {
      if (cancelled) return;
      if (u === null) {
        navigate('/admin/login', { replace: true });
      } else {
        setUsername(u);
      }
    });
    return () => { cancelled = true; };
  }, [navigate]);

  const logout = async () => {
    await gemini.adminLogout();
    navigate('/admin/login', { replace: true });
  };

  if (username === 'loading' || username === null) {
    return (
      <div className="vibe-classic h-screen w-full flex items-center justify-center bg-dyn-bg-primary text-dyn-text-muted text-sm">
        Ana tabbatarwa... (Checking session...)
      </div>
    );
  }

  return (
    <div className="vibe-classic h-screen w-full flex flex-col bg-dyn-bg-primary text-dyn-text-primary font-sans">
      <header className="px-6 sm:px-10 py-5 flex items-center justify-between border-b border-dyn-border/40">
        <div className="flex items-center gap-3">
          <ArewaLogo size={36} active />
          <div>
            <h1 className="font-serif italic text-xl text-dyn-accent tracking-tighter leading-none">Murya Admin</h1>
            <p className="text-[9px] uppercase tracking-[0.3em] text-dyn-text-muted mt-0.5">Review &amp; Corrections</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs text-dyn-text-secondary font-mono">{username}</span>
          <button
            onClick={() => setShowChangePassword(true)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-full text-[10px] font-black uppercase tracking-wider border border-dyn-border text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5 transition-all"
          >
            <KeyRound className="w-3.5 h-3.5" /> Kalmar Sirri (Password)
          </button>
          <button
            onClick={logout}
            className="flex items-center gap-1.5 px-4 py-2 rounded-full text-[10px] font-black uppercase tracking-wider border border-dyn-border text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5 transition-all"
          >
            <LogOut className="w-3.5 h-3.5" /> Fita (Logout)
          </button>
        </div>
      </header>

      <ChangePasswordDialog
        open={showChangePassword}
        onClose={() => setShowChangePassword(false)}
        onSuccess={() => navigate('/admin/login', { replace: true })}
      />

      {/* Tabs: text corrections vs pronunciation (voice) corrections */}
      <div className="px-6 sm:px-10 pt-5">
        <div className="flex gap-1 bg-dyn-bg-tertiary/60 p-1 rounded-full w-full sm:w-auto sm:inline-flex border border-dyn-border">
          {([
            { id: 'corrections', label: 'Gyaran Rubutu', sub: 'Text', icon: FileText },
            { id: 'pronunciation', label: 'Gyaran Furuci', sub: 'Voice', icon: Mic },
            { id: 'qa', label: 'Tambaya', sub: 'Q&A', icon: MessageSquare },
            { id: 'visitors', label: 'Ziyara', sub: 'Visitors', icon: Globe },
            { id: 'audit', label: 'Tarihi', sub: 'Audit log', icon: History },
          ] as const).map((t) => {
            const Icon = t.icon;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-5 py-2.5 rounded-full text-[10px] font-black uppercase tracking-wider transition-all whitespace-nowrap ${
                  tab === t.id
                    ? 'bg-dyn-accent text-dyn-bg-primary shadow-lg'
                    : 'text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5'
                }`}
              >
                <Icon className="w-3.5 h-3.5" /> {t.label} <span className="opacity-50">· {t.sub}</span>
              </button>
            );
          })}
        </div>
      </div>

      <main className="flex-1 overflow-y-auto p-6 sm:p-10 max-w-4xl w-full mx-auto">
        {tab === 'corrections' && <CorrectionsReview />}
        {tab === 'pronunciation' && <PronunciationReview />}
        {tab === 'qa' && <QAReview />}
        {tab === 'visitors' && <VisitorAnalytics />}
        {tab === 'audit' && <AuditLogView />}
      </main>
    </div>
  );
};
