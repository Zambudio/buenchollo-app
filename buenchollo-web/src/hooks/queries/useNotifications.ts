/** Hooks de React Query para notificaciones del usuario. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notificationsApi } from "@/services/api/notifications";
import { useAuth } from "@/hooks/useAuth";

const KEYS = {
  unreadCount: ["notifications", "unreadCount"] as const,
  list: ["notifications", "list"] as const,
};

/** Badge de notificaciones del header. Se refresca al volver a la pestaña
 *  para que el usuario vea actualizaciones sin recargar. */
export function useUnreadNotifications() {
  const { user } = useAuth();
  return useQuery({
    queryKey: KEYS.unreadCount,
    queryFn: () => notificationsApi.unreadCount().then((r) => r.count),
    enabled: !!user,
    // El badge es lo único que el usuario ve en cada navegación: refresco
    // agresivo en focus para que reaccione cuando vuelves al tab.
    refetchOnWindowFocus: true,
    // 30s de fresh: si el usuario abre el menú varias veces seguidas no
    // golpeamos la API cada vez.
    staleTime: 30 * 1000,
  });
}

/** Lista paginada de notificaciones (página de notificaciones). */
export function useNotificationsList() {
  const { user } = useAuth();
  return useQuery({
    queryKey: KEYS.list,
    queryFn: () => notificationsApi.list(),
    enabled: !!user,
    staleTime: 30 * 1000,
  });
}

/** Marca todas las notificaciones como leídas y refresca el badge y la lista. */
export function useMarkNotificationsRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => notificationsApi.markRead(),
    onSuccess: () => {
      // Invalidamos las queries afectadas: el badge baja a 0 y la lista
      // refleja todo leído sin escribir SQL en el cliente.
      qc.invalidateQueries({ queryKey: KEYS.unreadCount });
      qc.invalidateQueries({ queryKey: KEYS.list });
    },
  });
}
