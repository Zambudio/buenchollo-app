/** Unit test del helper de auth compartido: signInWithGoogle debe delegar
 *  en el cliente oficial de Supabase con el provider y la redirección
 *  correctos, sin lógica adicional propia. */
import { describe, expect, it, vi, beforeEach } from "vitest";

const signInWithOAuth = vi.fn();
vi.mock("@/integrations/supabase/client", () => ({
  supabase: { auth: { signInWithOAuth: (...args: unknown[]) => signInWithOAuth(...args) } },
}));

import { signInWithGoogle } from "@/lib/auth";

describe("signInWithGoogle", () => {
  beforeEach(() => {
    signInWithOAuth.mockReset();
  });

  it("llama a supabase.auth.signInWithOAuth con provider google y redirectTo al origen", async () => {
    signInWithOAuth.mockResolvedValue({ data: {}, error: null });
    await signInWithGoogle();
    expect(signInWithOAuth).toHaveBeenCalledWith({
      provider: "google",
      options: { redirectTo: window.location.origin },
    });
  });

  it("propaga el resultado devuelto por supabase", async () => {
    const result = { data: { provider: "google", url: "https://x" }, error: null };
    signInWithOAuth.mockResolvedValue(result);
    await expect(signInWithGoogle()).resolves.toBe(result);
  });
});
