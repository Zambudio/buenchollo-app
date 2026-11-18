/**
 * `localStorage` sin excepciones. Con las cookies bloqueadas (o en algunos modos
 * privados) solo acceder a `window.localStorage` lanza `SecurityError`; sin esta
 * protección, el banner de cookies tumbaba la página entera. Solo para
 * preferencias del navegador: nunca para datos que deban persistir seguro.
 */
export function getLocalStorage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

export function readLocal(key: string): string | null {
  try {
    return getLocalStorage()?.getItem(key) ?? null;
  } catch {
    return null;
  }
}

export function writeLocal(key: string, value: string): void {
  try {
    getLocalStorage()?.setItem(key, value);
  } catch {
    // Sin almacenamiento disponible: la preferencia dura solo esta visita.
  }
}
