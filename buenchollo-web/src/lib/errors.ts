/** Convierte cualquier valor capturado en un catch a un mensaje legible.
 *  Centraliza el manejo: en TypeScript moderno los catch son `unknown`, y
 *  hacer `e.message` revienta si lo lanzado no es un Error. */
export function errorMessage(e: unknown, fallback = "Error inesperado"): string {
  if (e instanceof Error) return e.message;
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
