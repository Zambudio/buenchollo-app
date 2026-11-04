import { supabase } from "@/integrations/supabase/client";
import { safeRedirect } from "@/lib/safe-redirect";

// Flujo OAuth de Google con Supabase, compartido por login y registro.
// Redirige de vuelta al origen actual (más `redirect`, si es una ruta segura).
export function signInWithGoogle(redirect?: string) {
  const path = safeRedirect(redirect);
  return supabase.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: path === "/" ? window.location.origin : window.location.origin + path },
  });
}
