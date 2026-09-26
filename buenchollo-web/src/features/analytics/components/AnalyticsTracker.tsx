import { useEffect } from "react";
import { useLocation } from "@tanstack/react-router";

import { useAuth } from "@/hooks/useAuth";
import { analyticsApi, attributionPayload } from "@/services/api/analytics";
import {
  getOrCreateSession,
  getOrCreateVisitor,
  isAnalyticsExcluded,
  resolveAttribution,
} from "@/features/analytics/lib/tracking";

const TRACK_DELAY_MS = 1_200;

export function AnalyticsTracker() {
  const location = useLocation();
  const { isAdmin, loading } = useAuth();

  useEffect(() => {
    if (loading || isAdmin || location.pathname.startsWith("/admin")) return;

    try {
      if (isAnalyticsExcluded(window.localStorage)) return;
    } catch {
      return;
    }

    let timeoutId: number | undefined;
    let cancelled = false;

    const track = () => {
      if (cancelled || document.visibilityState !== "visible") return;
      try {
        const now = Date.now();
        const attribution = resolveAttribution(
          new URL(window.location.href),
          document.referrer,
          window.location.hostname,
        );
        const visitorId = getOrCreateVisitor(window.localStorage, now, () => crypto.randomUUID());
        const session = getOrCreateSession(window.sessionStorage, attribution, now, () =>
          crypto.randomUUID(),
        );

        void analyticsApi
          .track({
            visitor_id: visitorId,
            session_id: session.id,
            path: window.location.pathname,
            ...attributionPayload(session.attribution),
          })
          .catch(() => {
            // La analítica nunca debe bloquear ni ensuciar la navegación pública.
          });
      } catch {
        // Navegadores sin almacenamiento disponible siguen funcionando sin medición.
      }
    };

    const schedule = () => {
      if (document.visibilityState !== "visible" || timeoutId !== undefined) return;
      timeoutId = window.setTimeout(track, TRACK_DELAY_MS);
    };

    schedule();
    document.addEventListener("visibilitychange", schedule);
    return () => {
      cancelled = true;
      if (timeoutId !== undefined) window.clearTimeout(timeoutId);
      document.removeEventListener("visibilitychange", schedule);
    };
  }, [isAdmin, loading, location.href, location.pathname]);

  return null;
}
