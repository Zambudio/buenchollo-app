import { supabase } from "@/integrations/supabase/client";

// Flujo OAuth de Google con Supabase, compartido por login y registro.
// Redirige de vuelta al origen actual tras autenticarse.
export function signInWithGoogle() {
  return supabase.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: window.location.origin },
  });
}
