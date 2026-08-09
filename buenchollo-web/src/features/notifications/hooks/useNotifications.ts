/** Hooks de React Query para notificaciones del usuario. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notificationsApi, type Notification } from "@/services/api/notifications";
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
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: KEYS.unreadCount });
      await qc.cancelQueries({ queryKey: KEYS.list });

      const prevCount = qc.getQueryData<number>(KEYS.unreadCount);
      const prevList = qc.getQueryData<Notification[]>(KEYS.list);

      qc.setQueryData<number>(KEYS.unreadCount, 0);
      qc.setQueryData<Notification[]>(
        KEYS.list,
        (old) => old?.map((n) => ({ ...n, is_read: true })) ?? [],
      );

      return { prevCount, prevList };
    },
    onError: (_err, _vars, context) => {
      if (context) {
        if (context.prevCount !== undefined) {
          qc.setQueryData(KEYS.unreadCount, context.prevCount);
        }
        if (context.prevList !== undefined) {
          qc.setQueryData(KEYS.list, context.prevList);
        }
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: KEYS.unreadCount });
      qc.invalidateQueries({ queryKey: KEYS.list });
    },
  });
}

/** Marca una única notificación como leída (p. ej. al pulsarla) y refresca el badge y la lista. */
export function useMarkNotificationRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => notificationsApi.markOneRead(id),
    onMutate: async (id: string) => {
      await qc.cancelQueries({ queryKey: KEYS.unreadCount });
      await qc.cancelQueries({ queryKey: KEYS.list });

      const prevCount = qc.getQueryData<number>(KEYS.unreadCount);
      const prevList = qc.getQueryData<Notification[]>(KEYS.list);

      if (prevList) {
        qc.setQueryData<Notification[]>(
          KEYS.list,
          (old) => old?.map((n) => (n.id === id ? { ...n, is_read: true } : n)) ?? [],
        );
      }

      if (typeof prevCount === "number") {
        qc.setQueryData<number>(KEYS.unreadCount, Math.max(0, prevCount - 1));
      }

      return { prevCount, prevList };
    },
    onError: (_err, _id, context) => {
      if (context) {
        if (context.prevCount !== undefined) {
          qc.setQueryData(KEYS.unreadCount, context.prevCount);
        }
        if (context.prevList !== undefined) {
          qc.setQueryData(KEYS.list, context.prevList);
        }
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: KEYS.unreadCount });
      qc.invalidateQueries({ queryKey: KEYS.list });
    },
  });
}
