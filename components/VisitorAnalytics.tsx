import React, { useEffect, useState } from 'react';
import { gemini } from '../services/localService.ts';
import { Activity, Globe, Users, RefreshCw } from 'lucide-react';

/** Privacy-preserving visitor analytics (Ziyara) — counts + rough geography by
 * browser timezone, no IP/PII. Admin-gated (GET /api/admin/analytics). */
export const VisitorAnalytics: React.FC = () => {
  const [analytics, setAnalytics] = useState<any>(null);

  const load = () => { setAnalytics(null); gemini.getAnalytics().then((d) => setAnalytics(d ?? { denied: true })); };
  useEffect(() => { load(); }, []);

  if (!analytics) return <div className="text-center py-10 text-dyn-text-secondary/40 font-mono text-xs animate-pulse">Ana ɗora bayanan ziyara…</div>;
  if (analytics.denied) return (
    <div className="text-center py-10 space-y-2">
      <div className="text-dyn-accent font-serif italic text-lg">Sai shiga na masu bita</div>
      <div className="text-dyn-text-secondary/60 font-mono text-xs">Wannan sashe na masu bita ne kaɗai. (Reviewer-only — sign in as admin.)</div>
    </div>
  );

  const daily = analytics.daily ?? [];
  const dailyMax = Math.max(1, ...daily.map((d: any) => d.visits));
  const countries = analytics.by_country ?? [];
  const countryMax = Math.max(1, ...countries.map((r: any) => r.visits));

  return (
    <div className="space-y-8 animate-reveal">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-serif italic text-xl text-dyn-text-primary">Ziyara</h3>
          <p className="text-[10px] uppercase tracking-widest text-dyn-text-muted">Visitors · privacy-preserving (no IP, by timezone)</p>
        </div>
        <button onClick={load} className="p-2 rounded-lg text-dyn-text-secondary hover:text-dyn-text-primary hover:bg-white/5" aria-label="Refresh"><RefreshCw className="w-4 h-4" /></button>
      </div>

      {/* Headline numbers */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        {[
          { label: 'Jimillar Ziyara', val: analytics.total_visits ?? 0, sub: 'Total visits (all time)' },
          { label: 'Na Yau', val: analytics.unique_devices?.today ?? 0, sub: 'Unique devices today' },
          { label: 'Kwana 7', val: analytics.unique_devices?.last_7d ?? 0, sub: 'Unique devices, last 7 days' },
          { label: 'Duka', val: analytics.unique_devices?.all_time ?? 0, sub: 'Unique devices, all time' },
        ].map((item, i) => (
          <div key={i} className="p-6 rounded-3xl bg-dyn-bg-tertiary/30 border border-dyn-border text-center hover:border-dyn-accent/40 transition-all shadow-xl">
            <span className="text-[9px] text-dyn-text-secondary uppercase tracking-widest block mb-3 font-semibold">{item.label}</span>
            <div className="text-4xl sm:text-5xl font-serif italic text-dyn-accent tabular-nums">{item.val}</div>
            <p className="text-[9px] text-dyn-text-muted mt-3 uppercase tracking-wider font-medium">{item.sub}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily trend */}
        <div className="p-6 rounded-3xl bg-dyn-bg-tertiary/20 border border-dyn-border">
          <h3 className="text-xs uppercase tracking-widest text-dyn-accent mb-5 font-bold flex items-center gap-2"><Activity className="w-4 h-4" /> Ziyara / Kullum (Daily visits)</h3>
          <div className="flex items-end gap-1 h-32">
            {daily.map((d: any, i: number) => (
              <div key={i} className="flex-1 flex flex-col items-center justify-end group" title={`${d.day}: ${d.visits} ziyara, ${d.unique} na'urori`}>
                <div className="w-full rounded-t bg-dyn-accent/70 group-hover:bg-dyn-accent transition-all" style={{ height: `${(d.visits / dailyMax) * 100}%`, minHeight: d.visits > 0 ? '3px' : '0' }}></div>
                <span className="text-[7px] text-dyn-text-muted mt-1 tabular-nums">{d.day?.slice(8)}</span>
              </div>
            ))}
          </div>
          <p className="text-[9px] text-dyn-text-muted mt-3 italic">Kwanaki na ƙarshe. (Last {daily.length} days.)</p>
        </div>

        {/* Geography */}
        <div className="p-6 rounded-3xl bg-dyn-bg-tertiary/20 border border-dyn-border">
          <h3 className="text-xs uppercase tracking-widest text-dyn-accent mb-5 font-bold flex items-center gap-2"><Globe className="w-4 h-4" /> Daga Ina (Where from)</h3>
          <div className="space-y-2">
            {countries.length === 0 && <p className="text-[10px] text-dyn-text-muted italic">Babu bayanai tukuna. (No data yet.)</p>}
            {countries.map((r: any, i: number) => (
              <div key={i} className="flex items-center gap-3">
                <span className="text-[11px] text-dyn-text-primary w-40 truncate">{r.country}</span>
                <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                  <div className="h-full bg-dyn-accent/70 rounded-full" style={{ width: `${(r.visits / countryMax) * 100}%` }}></div>
                </div>
                <span className="text-[10px] text-dyn-text-secondary font-mono tabular-nums w-8 text-right">{r.visits}</span>
              </div>
            ))}
          </div>
          <p className="text-[8px] text-dyn-text-muted/70 mt-4 italic">Ta yankin lokaci na na'ura (by device timezone — approximate, no IP tracked).</p>
        </div>
      </div>

      {/* Languages */}
      {(analytics.by_language ?? []).length > 0 && (
        <div className="p-6 rounded-3xl bg-dyn-bg-tertiary/20 border border-dyn-border">
          <h3 className="text-xs uppercase tracking-widest text-dyn-accent mb-4 font-bold flex items-center gap-2"><Users className="w-4 h-4" /> Harshen Na'ura (Browser language)</h3>
          <div className="flex flex-wrap gap-2">
            {(analytics.by_language ?? []).map((l: any, i: number) => (
              <span key={i} className="px-3 py-1.5 rounded-full bg-white/5 border border-dyn-border text-[10px] text-dyn-text-secondary font-mono">{l.lang} · {l.visits}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
