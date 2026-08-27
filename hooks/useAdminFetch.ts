import { DependencyList, useCallback, useEffect, useRef, useState } from "react";

/**
 * Shared fetch/loading/denied state for admin-gated GET endpoints.
 *
 * Before this hook, VisitorAnalytics.tsx and NeuralReview.tsx's "visitors"
 * tab each independently reimplemented the identical pattern: call a
 * gemini.get*() method that returns `null` on a 401/network failure, track
 * loading vs. loaded, and treat a `null`/`{denied:true}` result as "sign in
 * as admin" rather than "no data yet" (see docs/deep_scan_2026-08-23.md,
 * the Low-severity NeuralReview/VisitorAnalytics duplication finding). Two
 * independent copies of that logic is a real drift risk the next time the
 * response shape changes — one gets updated, the other silently doesn't.
 *
 * `fetcher` should follow the existing gemini.get*() convention: resolve to
 * the data on success, or `null` on denial/failure (never throw).
 */
export function useAdminFetch<T>(
  fetcher: () => Promise<T | null>,
  deps: DependencyList = []
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [denied, setDenied] = useState(false);
  // Guards against a slow, stale request landing after a newer one (e.g. the
  // caller re-runs the fetch on tab-switch faster than the network replies).
  const requestIdRef = useRef(0);

  const load = useCallback(() => {
    const requestId = ++requestIdRef.current;
    setLoading(true);
    fetcher().then((result) => {
      if (requestId !== requestIdRef.current) return; // superseded by a newer call
      setLoading(false);
      if (result === null) {
        setDenied(true);
        setData(null);
      } else {
        setDenied(false);
        setData(result);
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    load();
  }, [load]);

  return { data, loading, denied, reload: load };
}
