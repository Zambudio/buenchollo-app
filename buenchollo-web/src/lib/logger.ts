/**
 * Logger central de errores del frontend (cierra TD-08 y TD-14).
 *
 * Siempre escribe en consola (comportamiento previo). Si VITE_SENTRY_DSN
 * está configurado, además envía el error a Sentry: el SDK se carga con
 * import() dinámico en un chunk aparte, así que sin DSN no pesa ni un byte
 * en el bundle inicial y el logger queda inerte (mismo patrón que el
 * backend con SENTRY_DSN vacío).
 */

type SentryModule = typeof import("@sentry/react");

let sentry: SentryModule | null = null;

export async function initErrorTracking(): Promise<void> {
  const dsn = import.meta.env.VITE_SENTRY_DSN as string | undefined;
  if (!dsn || typeof window === "undefined") return;
  try {
    const mod = await import("@sentry/react");
    mod.init({
      dsn,
      environment: import.meta.env.MODE,
      // Sin PII: no enviamos IPs ni datos de usuario (coherente con SEC-09).
      sendDefaultPii: false,
      // Solo errores; el performance monitoring cobra cuota (ver backend).
      tracesSampleRate: 0,
    });
    sentry = mod;
  } catch (error) {
    console.error("No se pudo inicializar el error tracking:", error);
  }
}

/** Registra un error: consola siempre, Sentry si está inicializado. */
export function logError(message: string, error?: unknown): void {
  console.error(message, error ?? "");
  if (!sentry) return;
  if (error instanceof Error) {
    sentry.captureException(error, { extra: { message } });
  } else {
    sentry.captureMessage(error === undefined ? message : `${message} — ${String(error)}`, "error");
  }
}
