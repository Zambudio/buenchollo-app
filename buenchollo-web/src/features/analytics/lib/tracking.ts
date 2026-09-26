export type AnalyticsSource = "telegram" | "organic" | "referral" | "direct";

export interface Attribution {
  source: AnalyticsSource;
  sourceDetail: string;
  medium: string;
  campaign: string | null;
  referrerHost: string | null;
}

export interface AnalyticsSession {
  id: string;
  lastActivityAt: number;
  attribution: Attribution;
}

export const SESSION_IDLE_MS = 30 * 60 * 1000;
export const VISITOR_TTL_MS = 395 * 24 * 60 * 60 * 1000;

const VISITOR_KEY = "bct.analytics.visitor.v1";
const SESSION_KEY = "bct.analytics.session.v1";
const EXCLUDED_KEY = "bct.analytics.excluded.v1";

const SEARCH_ENGINES: ReadonlyArray<[RegExp, string]> = [
  [/(^|\.)google\./, "google"],
  [/(^|\.)bing\.com$/, "bing"],
  [/(^|\.)duckduckgo\.com$/, "duckduckgo"],
  [/(^|\.)yahoo\./, "yahoo"],
  [/(^|\.)ecosia\.org$/, "ecosia"],
  [/(^|\.)brave\.com$/, "brave"],
];

function normalizedHost(host: string): string {
  return host.toLowerCase().replace(/^www\./, "");
}

function referrerHost(referrer: string): string | null {
  if (!referrer) return null;
  try {
    return normalizedHost(new URL(referrer).hostname);
  } catch {
    return null;
  }
}

export function resolveAttribution(url: URL, referrer: string, siteHost: string): Attribution {
  const host = referrerHost(referrer);
  const ownHost = normalizedHost(siteHost);
  const utmSource = url.searchParams.get("utm_source")?.trim().toLowerCase() ?? "";
  const utmMedium = url.searchParams.get("utm_medium")?.trim().toLowerCase() ?? "";
  const campaign = url.searchParams.get("utm_campaign")?.trim() || null;

  if (utmSource === "telegram") {
    return {
      source: "telegram",
      sourceDetail: "telegram",
      medium: utmMedium || "social",
      campaign,
      referrerHost: host,
    };
  }

  if (utmSource) {
    return {
      source: utmMedium === "organic" ? "organic" : "referral",
      sourceDetail: utmSource.slice(0, 100),
      medium: (utmMedium || "campaign").slice(0, 50),
      campaign,
      referrerHost: host,
    };
  }

  if (host && host !== ownHost) {
    if (host === "t.me" || host.endsWith(".telegram.org")) {
      return {
        source: "telegram",
        sourceDetail: "telegram",
        medium: "social",
        campaign: null,
        referrerHost: host,
      };
    }

    const engine = SEARCH_ENGINES.find(([pattern]) => pattern.test(host));
    if (engine) {
      return {
        source: "organic",
        sourceDetail: engine[1],
        medium: "organic",
        campaign: null,
        referrerHost: host,
      };
    }

    return {
      source: "referral",
      sourceDetail: host.slice(0, 100),
      medium: "referral",
      campaign: null,
      referrerHost: host,
    };
  }

  return {
    source: "direct",
    sourceDetail: "direct",
    medium: "none",
    campaign: null,
    referrerHost: host,
  };
}

export function getOrCreateVisitor(storage: Storage, now: number, createId: () => string): string {
  try {
    const stored = JSON.parse(storage.getItem(VISITOR_KEY) ?? "null") as {
      v?: number;
      id?: string;
      expiresAt?: number;
    } | null;
    if (
      stored?.v === 1 &&
      stored.id &&
      typeof stored.expiresAt === "number" &&
      stored.expiresAt > now
    ) {
      return stored.id;
    }
  } catch {
    // Un valor antiguo o manipulado se sustituye por una identidad nueva.
  }

  const id = createId();
  storage.setItem(VISITOR_KEY, JSON.stringify({ v: 1, id, expiresAt: now + VISITOR_TTL_MS }));
  return id;
}

export function isAnalyticsExcluded(storage: Storage): boolean {
  return storage.getItem(EXCLUDED_KEY) === "1";
}

export function setAnalyticsExcluded(storage: Storage, excluded: boolean): void {
  if (excluded) storage.setItem(EXCLUDED_KEY, "1");
  else storage.removeItem(EXCLUDED_KEY);
}

export function getOrCreateSession(
  storage: Storage,
  attribution: Attribution,
  now: number,
  createId: () => string,
): AnalyticsSession {
  try {
    const stored = JSON.parse(storage.getItem(SESSION_KEY) ?? "null") as {
      v?: number;
      id?: string;
      lastActivityAt?: number;
      attribution?: Attribution;
    } | null;
    if (
      stored?.v === 1 &&
      stored.id &&
      typeof stored.lastActivityAt === "number" &&
      now - stored.lastActivityAt < SESSION_IDLE_MS &&
      stored.attribution
    ) {
      const session = { id: stored.id, lastActivityAt: now, attribution: stored.attribution };
      storage.setItem(SESSION_KEY, JSON.stringify({ v: 1, ...session }));
      return session;
    }
  } catch {
    // Un valor antiguo o manipulado inicia una sesión limpia.
  }

  const session = { id: createId(), lastActivityAt: now, attribution };
  storage.setItem(SESSION_KEY, JSON.stringify({ v: 1, ...session }));
  return session;
}
