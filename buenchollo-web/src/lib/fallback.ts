import { logError } from "@/lib/logger";

/**
 * Resuelve con `fallback` si la petición falla, registrando el error.
 * Pensado para loaders: un bloque secundario caído no debe tumbar la página.
 */
export function withFallback<T>(promise: Promise<T>, fallback: T, message: string): Promise<T> {
  return promise.catch((error: unknown) => {
    logError(message, error);
    return fallback;
  });
}
