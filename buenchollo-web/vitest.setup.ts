/**
 * Setup global para los tests con Vitest + Testing Library.
 *
 * - `@testing-library/jest-dom/vitest`: matchers como toBeInTheDocument,
 *   toHaveTextContent, etc.
 * - cleanup automático tras cada test para que el DOM no se contamine
 *   entre casos.
 * - Mock de supabase.auth: muchos componentes resuelven la sesión al
 *   montar y revientarían sin esto. El cliente Supabase requiere ENV
 *   vars que no existen en el entorno de tests.
 */
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

afterEach(() => {
  cleanup();
});

// Mock de @/integrations/supabase/client: devuelve un cliente inerte que
// los componentes pueden invocar sin reventar. Los tests que necesiten
// comportamiento específico pueden sobreescribir con vi.mock local.
vi.mock("@/integrations/supabase/client", () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
      onAuthStateChange: vi.fn().mockReturnValue({
        data: { subscription: { unsubscribe: vi.fn() } },
      }),
      signOut: vi.fn().mockResolvedValue({ error: null }),
      signInWithOAuth: vi.fn(),
      signInWithPassword: vi.fn(),
      signUp: vi.fn(),
    },
    from: vi.fn(),
    storage: { from: vi.fn() },
  },
}));
