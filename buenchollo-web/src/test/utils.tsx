/** Utilidades compartidas para tests con Testing Library.
 *
 *  Centraliza el render con providers (QueryClientProvider) para que cada
 *  test no monte su propio andamiaje. Los tests siguen siendo responsables
 *  de mockear `useAuth`, hooks de queries y `@tanstack/react-router` según
 *  necesiten.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions, type RenderResult } from "@testing-library/react";
import type { ReactElement } from "react";

/** Crea un QueryClient con reintentos desactivados para tests deterministas. */
export function buildTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

interface ProvidersOptions extends Omit<RenderOptions, "wrapper"> {
  queryClient?: QueryClient;
}

/** Renderiza el componente envuelto en QueryClientProvider. */
export function renderWithProviders(
  ui: ReactElement,
  { queryClient = buildTestQueryClient(), ...options }: ProvidersOptions = {},
): RenderResult & { queryClient: QueryClient } {
  const result = render(ui, {
    wrapper: ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    ),
    ...options,
  });
  return { ...result, queryClient };
}
