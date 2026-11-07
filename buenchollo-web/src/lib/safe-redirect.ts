const MAX_REDIRECT_LENGTH = 2048;

/** Devuelve `value` solo si es una ruta relativa del propio sitio; si no, "/".
 *  Evita open redirects (`//host`, `/\host`, esquemas, caracteres de control). */
export function safeRedirect(value: unknown): string {
  if (typeof value !== "string") return "/";
  if (value.length === 0 || value.length > MAX_REDIRECT_LENGTH) return "/";
  if (!value.startsWith("/") || value.startsWith("//")) return "/";
  // eslint-disable-next-line no-control-regex
  if (value.includes("\\") || /[\u0000-\u001f\u007f]/.test(value)) return "/";
  try {
    const parsed = new URL(value, "http://safe-redirect.invalid");
    if (parsed.origin !== "http://safe-redirect.invalid") return "/";
  } catch {
    return "/";
  }
  return value;
}

export function loginSearch(redirect: string | undefined): { redirect?: string } {
  const safe = safeRedirect(redirect);
  return safe === "/" ? {} : { redirect: safe };
}

/** `loginSearch` para volver a la página actual (solo en el navegador). */
export function currentPageLoginSearch(): { redirect?: string } {
  if (typeof window === "undefined") return {};
  return loginSearch(window.location.pathname + window.location.search);
}
