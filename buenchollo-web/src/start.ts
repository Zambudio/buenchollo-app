/**
 * Instancia global de TanStack Start.
 *
 * Añade cabeceras de seguridad a todas las respuestas SSR del Worker (la API
 * ya las emite desde `buenchollo-api/app/core/security_headers.py`).
 *
 * No se fija una CSP de scripts: el SSR inyecta scripts inline de hidratación
 * y una CSP estricta sin nonces rompería la web. `frame-ancestors` sí es
 * seguro porque no restringe nada de lo que carga la propia página.
 */
import { createMiddleware, createStart } from "@tanstack/react-start";

const SECURITY_HEADERS: Record<string, string> = {
  "Content-Security-Policy": "frame-ancestors 'none'",
  "X-Frame-Options": "DENY",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy": "camera=(), geolocation=(), microphone=(), payment=(), usb=()",
};

const securityHeaders = createMiddleware({ type: "request" }).server(async ({ next }) => {
  const result = await next();
  let response = result.response;
  try {
    for (const [name, value] of Object.entries(SECURITY_HEADERS)) {
      response.headers.set(name, value);
    }
  } catch {
    // Cabeceras inmutables (p. ej. una Response proveniente de fetch): se copia.
    response = new Response(response.body, response);
    for (const [name, value] of Object.entries(SECURITY_HEADERS)) {
      response.headers.set(name, value);
    }
  }
  return { ...result, response };
});

export const startInstance = createStart(() => ({
  requestMiddleware: [securityHeaders],
}));
