/**
 * «Novedades desde tu última visita», sin cuenta: el navegador recuerda cuándo
 * estuvo aquí por última vez. Una visita termina tras 30 minutos sin actividad
 * (cargar o navegar entre páginas, o volver a la pestaña; ver `touchVisit`);
 * entonces la referencia pasa a ser el final de la anterior. Funciona igual
 * con varias pestañas abiertas (todo vive en localStorage).
 */
import { readLocal, writeLocal } from "./storage";

export const VISIT_KEY = "bct:visit";
export const VISIT_GAP_MS = 30 * 60 * 1000;

export interface VisitState {
  /** Final de la visita anterior: lo publicado después es «nuevo». */
  baseline: string | null;
  /** Última página cargada en esta visita. */
  lastSeen: string;
}

/** Estado tras cargar una página ahora (función pura, para poder probarla). */
export function nextVisitState(stored: VisitState | null, now: Date): VisitState {
  const nowIso = now.toISOString();
  if (!stored) return { baseline: null, lastSeen: nowIso };
  const gap = now.getTime() - new Date(stored.lastSeen).getTime();
  if (Number.isFinite(gap) && gap >= 0 && gap < VISIT_GAP_MS) {
    return { baseline: stored.baseline, lastSeen: nowIso };
  }
  return { baseline: stored.lastSeen, lastSeen: nowIso };
}

function readState(): VisitState | null {
  const raw = readLocal(VISIT_KEY);
  if (!raw) return null;
  try {
    const value = JSON.parse(raw) as Partial<VisitState>;
    if (typeof value.lastSeen !== "string" || Number.isNaN(Date.parse(value.lastSeen))) return null;
    const baseline =
      typeof value.baseline === "string" && !Number.isNaN(Date.parse(value.baseline))
        ? value.baseline
        : null;
    return { baseline, lastSeen: value.lastSeen };
  } catch {
    return null;
  }
}

let cached: Date | null | undefined;

/**
 * Referencia de esta carga de página (se calcula una vez y la comparten la
 * cabecera y la portada). Solo en el navegador: null en el servidor y en la
 * primera visita.
 */
export function visitBaseline(now: Date = new Date()): Date | null {
  if (typeof window === "undefined") return null;
  if (cached !== undefined) return cached;
  const next = nextVisitState(readState(), now);
  writeLocal(VISIT_KEY, JSON.stringify(next));
  cached = next.baseline ? new Date(next.baseline) : null;
  return cached;
}

/**
 * Mantiene viva la visita: se llama al navegar dentro de la web y al volver a
 * la pestaña. No cambia la referencia ya calculada para esta carga de página.
 */
export function touchVisit(now: Date = new Date()): void {
  if (typeof window === "undefined") return;
  writeLocal(VISIT_KEY, JSON.stringify(nextVisitState(readState(), now)));
}

/** Solo para tests. */
export function resetVisitBaselineCache(): void {
  cached = undefined;
}
