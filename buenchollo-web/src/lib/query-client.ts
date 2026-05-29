/** Configuración compartida del QueryClient de TanStack Query.
 *
 *  Por qué TanStack Query: deduplica peticiones, cachea por staleTime,
 *  refetch automático al recuperar el foco y al reconectar. Convierte
 *  componentes con 30 líneas de useEffect en un useQuery de 3 líneas y
 *  elimina cargas duplicadas cuando varios componentes piden el mismo dato.
 *
 *  Defaults conservadores para una API que sirve datos relativamente
 *  estáticos (chollos, categorías). Cada hook puede sobrescribir
 *  staleTime/gcTime según necesite.
 */
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Cuánto tiempo los datos se consideran "frescos" antes de refetch.
      // 60s evita ráfagas de peticiones cuando el usuario navega rápido.
      staleTime: 60 * 1000,
      // Cuánto retiene la caché tras desuso. 5 min = cuando vuelves a una
      // pantalla ya vista, se muestra al instante.
      gcTime: 5 * 60 * 1000,
      // Sólo refetch en focus para datos críticos. Por defecto desactivado
      // para no spam-ear; los hooks que lo necesiten lo activan.
      refetchOnWindowFocus: false,
      // Reintentos: 1 vez basta para errores transitorios de red.
      retry: 1,
    },
  },
});
