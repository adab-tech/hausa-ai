import React, { useState } from 'react';
import { gemini } from '../services/localService.ts';
import { useAdminFetch } from '../hooks/useAdminFetch.ts';
import { AlertTriangle, CheckCircle2, Clock, Download, Loader2, RefreshCw, XCircle } from 'lucide-react';

const CONDITION_LABEL: Record<string, string> = {
  murya: 'Murya', ground_truth: 'Muryar Ɗan Adam (Human recording)',
};

function StatBar({ label, mean, n, color }: { label: string; mean: number | null; n: number; color: string }) {
  const pct = mean !== null ? ((mean - 1) / 4) * 100 : 0;
  return (
    <div className="flex items-center gap-3 py-2 border-b border-dyn-border/30 last:border-0">
      <div className="w-32 shrink-0 text-xs font-bold text-dyn-text-primary truncate">{label}</div>
      <div className="flex-1 h-2.5 rounded-full bg-dyn-bg-tertiary/60 overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <div className="w-28 shrink-0 text-right text-[11px] font-mono text-dyn-text-muted">
        {mean !== null ? `${mean.toFixed(2)} (n=${n})` : 'n/a'}
      </div>
    </div>
  );
}

/** ADMIN: the eval gate before a voice checkpoint or correction batch feeds
 * the next retrain — a synthesized read of the MOS listening test's results,
 * plus an explicit, auditable decision the admin records on top of it.
 * Nothing here ships anything by itself; recording a decision is a note for
 * whoever runs the next retrain, same as approving a pronunciation
 * correction doesn't retrain the model on its own. */
export const MosReview: React.FC = () => {
  const { data, loading, denied, reload } = useAdminFetch(() => gemini.getMosResults());
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  if (denied) return <p className="text-dyn-text-muted text-sm p-4">An hana shiga. (Admin login required.)</p>;
  if (loading && !data) return <div className="flex justify-center py-10"><Loader2 className="w-5 h-5 animate-spin text-dyn-accent" /></div>;
  if (!data) return null;

  const { results, decisions } = data;
  const { analysis } = results;

  const verdictStyle = {
    close_to_human: { icon: CheckCircle2, color: 'text-emerald-400', border: 'border-emerald-500/30', bg: 'bg-emerald-500/[0.05]' },
    meaningful_gap: { icon: AlertTriangle, color: 'text-amber-400', border: 'border-amber-500/30', bg: 'bg-amber-500/[0.05]' },
    insufficient_data: { icon: Clock, color: 'text-dyn-text-muted', border: 'border-dyn-border', bg: 'bg-dyn-bg-tertiary/20' },
  }[analysis.verdict];
  const VerdictIcon = verdictStyle.icon;

  const decide = async (verdict: 'approved_for_training' | 'needs_more_data' | 'rejected') => {
    setBusy(verdict);
    const ok = await gemini.recordMosDecision(verdict, note.trim() || undefined);
    setBusy(null);
    if (ok) { setNote(''); reload(); }
    else alert('Ajiyewa ya kāsa. Ka sāke gwadawa. (Save failed — try again.)');
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h3 className="font-serif italic text-xl text-dyn-text-primary">Kimanta Murya</h3>
          <p className="text-[10px] uppercase tracking-widest text-dyn-text-muted">TTS Evaluation · MOS listening test</p>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="text-dyn-text-secondary">{results.total_ratings} ratings · {results.session_count} sessions</span>
          {results.total_ratings > 0 && (
            <button
              onClick={async () => { setExporting(true); const ok = await gemini.exportMosRatings(); setExporting(false); if (!ok) alert('Fitarwa ya kāsa. (Export failed.)'); }}
              disabled={exporting}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-dyn-accent/40 text-dyn-accent text-[10px] font-bold uppercase tracking-wider hover:bg-dyn-accent/10 disabled:opacity-40"
              title="Download every raw rating as CSV for offline analysis"
            >
              {exporting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />} Fitar (Export CSV)
            </button>
          )}
          <button onClick={reload} className="p-2 rounded-lg text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5" aria-label="Refresh"><RefreshCw className="w-4 h-4" /></button>
        </div>
      </div>

      {/* Headline analysis — the summary, before the raw table */}
      <div className={`rounded-2xl border ${verdictStyle.border} ${verdictStyle.bg} p-5 flex items-start gap-3`}>
        <VerdictIcon className={`w-5 h-5 mt-0.5 shrink-0 ${verdictStyle.color}`} />
        <div className="space-y-1">
          <p className="text-sm text-dyn-text-primary leading-relaxed">{analysis.headline}</p>
          {analysis.weak_voices.length > 0 && (
            <p className="text-xs text-amber-400/90">
              Waɗannan muryoyi suna buƙatar kulawa (voices needing attention): {analysis.weak_voices.map((w) => `${w.voice} (${w.mean.toFixed(2)}, n=${w.n})`).join(', ')}
            </p>
          )}
          {analysis.intelligibility_flag && (
            <p className="text-xs text-amber-400/90">
              Kashi {analysis.intelligibility_pct_full}% ne kawai suka fahimci kowace kalma — ƙasa da yadda ake tsammani. (Only {analysis.intelligibility_pct_full}% understood every word — lower than expected.)
            </p>
          )}
        </div>
      </div>

      {/* Raw stats */}
      {results.total_ratings > 0 && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-dyn-border p-5">
            <p className="text-[10px] uppercase tracking-widest text-dyn-text-muted font-bold mb-3">Ta Nau'i (By condition)</p>
            {Object.entries(results.by_condition).map(([cond, stat]) => (
              <StatBar key={cond} label={CONDITION_LABEL[cond] ?? cond} mean={stat.mean} n={stat.n}
                color={cond === 'ground_truth' ? '#34d399' : 'var(--accent-color)'} />
            ))}
          </div>

          {Object.keys(results.by_voice).length > 0 && (
            <div className="rounded-2xl border border-dyn-border p-5">
              <p className="text-[10px] uppercase tracking-widest text-dyn-text-muted font-bold mb-3">Murya, Ta Murya-Murya (By voice)</p>
              {Object.entries(results.by_voice).sort(([a], [b]) => a.localeCompare(b)).map(([voice, stat]) => (
                <StatBar key={voice} label={voice} mean={stat.mean} n={stat.n} color="var(--accent-color)" />
              ))}
            </div>
          )}

          <div className="rounded-2xl border border-dyn-border p-5">
            <p className="text-[10px] uppercase tracking-widest text-dyn-text-muted font-bold mb-3">Fahimta (Intelligibility)</p>
            <div className="flex gap-3">
              <div className="flex-1 rounded-xl bg-dyn-bg-tertiary/30 p-3 text-center">
                <div className="font-mono text-lg text-emerald-400">{results.intelligibility.yes}</div>
                <div className="text-[10px] text-dyn-text-muted">Duka (Full)</div>
              </div>
              <div className="flex-1 rounded-xl bg-dyn-bg-tertiary/30 p-3 text-center">
                <div className="font-mono text-lg text-amber-400">{results.intelligibility.partial}</div>
                <div className="text-[10px] text-dyn-text-muted">Yawanci (Mostly)</div>
              </div>
              <div className="flex-1 rounded-xl bg-dyn-bg-tertiary/30 p-3 text-center">
                <div className="font-mono text-lg text-red-400">{results.intelligibility.no}</div>
                <div className="text-[10px] text-dyn-text-muted">A'a (Unclear)</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Explicit admin decision — the actual "final authority" record */}
      <div className="rounded-2xl border border-dyn-border bg-dyn-bg-tertiary/30 p-5 space-y-3">
        <label className="text-[10px] uppercase tracking-widest text-dyn-text-muted font-bold">Yanke Shawara (Record your decision)</label>
        <p className="text-xs text-dyn-text-muted/80">Wannan bai aika komai zuwa horo ba kai tsaye — rikodi ne kawai na abin da ka yanke. (This never ships anything to training by itself — it's just an auditable record of your call.)</p>
        <input value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} placeholder="Bayani (optional note)…"
          className="w-full rounded-xl bg-dyn-bg-tertiary/50 border border-dyn-border px-4 py-2.5 text-sm text-dyn-text-primary focus:outline-none focus:border-dyn-accent/50" />
        <div className="flex items-center gap-2 flex-wrap">
          <button onClick={() => decide('approved_for_training')} disabled={busy !== null}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-500/20 border border-emerald-500/50 text-emerald-400 text-[11px] font-bold uppercase hover:bg-emerald-500/30 disabled:opacity-40">
            {busy === 'approved_for_training' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />} Amince don Horo (Approve for training)
          </button>
          <button onClick={() => decide('needs_more_data')} disabled={busy !== null}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-amber-500/20 border border-amber-500/50 text-amber-400 text-[11px] font-bold uppercase hover:bg-amber-500/30 disabled:opacity-40">
            {busy === 'needs_more_data' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Clock className="w-3.5 h-3.5" />} Bukatar Ƙarin Bayani (Needs more data)
          </button>
          <button onClick={() => decide('rejected')} disabled={busy !== null}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-red-500/20 border border-red-500/50 text-red-400 text-[11px] font-bold uppercase hover:bg-red-500/30 disabled:opacity-40">
            {busy === 'rejected' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <XCircle className="w-3.5 h-3.5" />} Ƙi (Reject)
          </button>
        </div>
      </div>

      {/* Decision history */}
      {decisions.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] uppercase tracking-widest text-dyn-text-muted font-bold">Tarihin Shawarwari (Decision history)</p>
          {decisions.map((d) => (
            <div key={d.id} className="flex items-start justify-between gap-3 rounded-xl border border-dyn-border bg-dyn-bg-tertiary/20 px-4 py-3">
              <div className="min-w-0">
                <p className="text-sm text-dyn-text-primary font-bold capitalize">{d.verdict.replace(/_/g, ' ')}</p>
                {d.note && <p className="text-xs text-dyn-text-secondary mt-0.5">{d.note}</p>}
                <p className="text-[10px] text-dyn-text-muted mt-1">
                  {d.admin} · {new Date(d.created_at * 1000).toLocaleString()} · at the time: Murya {d.murya_mean_at_time?.toFixed(2) ?? 'n/a'}
                  {d.ground_truth_mean_at_time !== null && `, human ${d.ground_truth_mean_at_time.toFixed(2)}`}
                  {` (${d.total_ratings_at_time} ratings)`}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
