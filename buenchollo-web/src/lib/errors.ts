export const NETWORK_ERROR_MESSAGE =
  "No se pudo conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.";

interface ApiErrorLike {
  name: "ApiError";
  status: number;
  message: string;
}

function isApiError(e: unknown): e is ApiErrorLike {
  return e instanceof Error && e.name === "ApiError" && "status" in e;
}

function isNetworkError(e: unknown): boolean {
  // fetch lanza TypeError sin conexión; el timeout del cliente aborta la petición.
  if (e instanceof TypeError) return true;
  return e instanceof Error && (e.name === "AbortError" || e.name === "TimeoutError");
}

/** Convierte cualquier valor capturado en un catch en un mensaje para el usuario.
 *
 *  - Errores 4xx de la API: el `detail` del backend (los errores de dominio ya
 *    llegan en español). Una validación (422) se muestra como «Datos no válidos».
 *  - Errores 5xx: el `fallback` del llamante; nunca detalles internos.
 *  - Sin conexión o tiempo agotado: un mensaje de conexión en español.
 *  - Otros `Error` lanzados por la propia app: su mensaje. */
export function errorMessage(
  e: unknown,
  fallback = "Ha ocurrido un error inesperado. Inténtalo de nuevo.",
): string {
  if (isApiError(e)) {
    // El cliente pone en `message` el `detail` del backend o, si no hay,
    // «API Error: <código> <texto>», que no se enseña al usuario.
    if (e.status >= 500 || !e.message || e.message.startsWith("API Error:")) return fallback;
    if (e.status === 422) return `Datos no válidos: ${e.message}`;
    return e.message;
  }
  if (isNetworkError(e)) return NETWORK_ERROR_MESSAGE;
  if (e instanceof Error) return e.message || fallback;
  if (typeof e === "string") return e;
  return fallback;
}

/** Traduce mensajes de error técnicos de Supabase Auth a español claro y amigable. */
export function translateAuthError(
  message?: string | null,
  fallback = "Ha ocurrido un error al procesar la solicitud",
): string {
  if (!message) return fallback;

  // "For security purposes, you can only request this after 28 seconds."
  const secondsMatch = message.match(/after (\d+) seconds/i);
  if (secondsMatch) {
    const secs = secondsMatch[1];
    return `Por seguridad, debes esperar ${secs} segundos antes de volver a solicitar otro correo.`;
  }

  const lower = message.toLowerCase();
  if (lower.includes("rate limit") || lower.includes("too many requests")) {
    return "Has realizado demasiados intentos. Por favor, espera unos instantes.";
  }
  if (lower.includes("user already registered") || lower.includes("already exists")) {
    return "Ya existe una cuenta con este correo electrónico. Inicia sesión o recupera tu contraseña.";
  }
  if (lower.includes("email not confirmed")) {
    return "Debes confirmar tu correo electrónico antes de entrar. Revisa tu bandeja de entrada.";
  }
  if (lower.includes("invalid login credentials") || lower.includes("invalid credentials")) {
    return "Correo o contraseña incorrectos.";
  }
  if (lower.includes("password should be at least") || lower.includes("password is too short")) {
    return "La contraseña debe tener al menos 6 caracteres.";
  }
  if (lower.includes("email link is invalid or has expired") || lower.includes("otp_expired")) {
    return "El enlace de confirmación ha caducado o ya ha sido utilizado.";
  }
  if (lower.includes("token has expired") || lower.includes("token is invalid")) {
    return "El enlace de seguridad ha caducado o no es válido.";
  }

  return message;
}
