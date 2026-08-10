import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Bell, Info, CheckCheck } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  useUnreadNotifications,
  useNotificationsList,
  useMarkNotificationsRead,
  useMarkNotificationRead,
} from "@/features/notifications/hooks/useNotifications";
import type { Notification } from "@/services/api/notifications";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

function formatNotificationDate(dateStr: string | Date | null | undefined): string {
  if (!dateStr) return "";
  const d = typeof dateStr === "string" ? new Date(dateStr) : dateStr;
  if (!d || isNaN(d.getTime())) return "";
  return `${d.getDate()}/${d.getMonth() + 1}/${d.getFullYear()}`;
}

export function NotificationsPopover() {
  const [open, setOpen] = useState(false);
  const nav = useNavigate();
  const { data: unread = 0 } = useUnreadNotifications();
  const { data: items = [], isLoading } = useNotificationsList();
  const markRead = useMarkNotificationsRead();
  const markOneRead = useMarkNotificationRead();

  const handleMarkAllRead = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (markRead.isPending) return;

    markRead.mutate(undefined, {
      onSuccess: () => {
        toast.success("Notificaciones marcadas como leídas");
      },
      onError: () => {
        toast.error("No se pudieron marcar las notificaciones como leídas");
      },
    });
  };

  const handleItemClick = (n: Notification) => {
    setOpen(false);
    if (!n.is_read) {
      markOneRead.mutate(n.id);
    }
    if (n.link_url) {
      nav({ to: n.link_url });
    } else if (n.deal_id) {
      nav({ to: `/chollo/${n.deal_id}` });
    }
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label="Notificaciones"
          title="Notificaciones"
          className="relative p-2 hover:text-cyan-glow transition-colors outline-none cursor-pointer rounded-full"
        >
          <Bell className="size-5" />
          {unread > 0 && (
            <span className="absolute -top-0.5 -right-0.5 bg-alert-red text-white text-[10px] font-mono font-bold rounded-full size-4 flex items-center justify-center animate-in fade-in zoom-in-75">
              {unread > 9 ? "9+" : unread}
            </span>
          )}
        </button>
      </PopoverTrigger>

      <PopoverContent
        align="end"
        sideOffset={8}
        className="w-80 sm:w-96 p-0 overflow-hidden rounded-2xl border border-surface-700/80 dark:border-surface-700 shadow-2xl bg-surface-800 text-foreground z-50 animate-in fade-in-0 zoom-in-95 data-[side=bottom]:slide-in-from-top-2"
      >
        {/* Cabecera azul corporativo */}
        <div className="bg-[#156287] dark:bg-[#0f4d68] text-white px-4 py-3 sm:py-3.5 flex items-center justify-between select-none">
          <h3 className="font-bold text-base sm:text-lg tracking-tight text-white m-0">
            Notificaciones
          </h3>

          {unread > 0 && (
            <button
              type="button"
              onClick={handleMarkAllRead}
              disabled={markRead.isPending}
              title="Marcar todas como leídas"
              className="text-xs font-medium text-sky-100 hover:text-white bg-[#0f4d68] hover:bg-[#0b3c53] dark:bg-[#156287] dark:hover:bg-[#1a749e] active:scale-95 px-2.5 py-1 rounded-lg transition-all border border-sky-400/30 cursor-pointer flex items-center gap-1 shrink-0 disabled:opacity-50"
            >
              <CheckCheck className="size-3.5" />
              <span>Marcar todas como leídas</span>
            </button>
          )}
        </div>

        {/* Lista de notificaciones con scroll */}
        <div className="max-h-[380px] sm:max-h-[420px] overflow-y-auto divide-y divide-surface-700/20 dark:divide-surface-700/40 bg-surface-800 dark:bg-surface-900">
          {isLoading ? (
            <div className="p-6 space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-start gap-3 animate-pulse">
                  <div className="size-9 rounded-full bg-surface-700/50 shrink-0" />
                  <div className="flex-1 space-y-2">
                    <div className="h-3.5 bg-surface-700/50 rounded w-3/4" />
                    <div className="h-3 bg-surface-700/30 rounded w-full" />
                  </div>
                </div>
              ))}
            </div>
          ) : items.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground font-mono text-xs">
              <Bell className="size-8 mx-auto mb-2 text-muted-foreground/40" />
              <p>Sin notificaciones por ahora.</p>
              <p className="text-[11px] text-muted-foreground/70 mt-1">
                Crea alertas para recibir avisos cuando aparezcan chollos.
              </p>
            </div>
          ) : (
            items.map((n) => {
              const displayBody = n.body ? n.body.replace(/^Nuevo chollo:\s*/i, "") : "";
              const formattedDate = formatNotificationDate(n.created_at);

              return (
                <button
                  key={n.id}
                  type="button"
                  onClick={() => handleItemClick(n)}
                  className={cn(
                    "w-full text-left p-3.5 sm:p-4 flex items-start gap-3 border-l-2 transition-colors hover:bg-surface-700/25 dark:hover:bg-surface-700/40 cursor-pointer group focus-visible:bg-surface-700/30 focus-visible:outline-none",
                    !n.is_read
                      ? "border-cyan-glow bg-cyan-glow/10 dark:bg-cyan-glow/[0.08]"
                      : "border-transparent",
                  )}
                >
                  {/* Icono Info circular */}
                  <div
                    className={cn(
                      "size-9 sm:size-10 rounded-full border flex items-center justify-center shrink-0 mt-0.5 transition-colors",
                      !n.is_read
                        ? "border-cyan-glow/50 bg-cyan-glow/15 text-cyan-glow"
                        : "border-surface-600/30 dark:border-surface-600/40 bg-surface-700/20 dark:bg-surface-800 text-foreground/70 group-hover:border-cyan-glow/50 group-hover:text-cyan-glow",
                    )}
                  >
                    <Info className="size-4 sm:size-5" />
                  </div>

                  {/* Contenido */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline justify-between gap-2">
                      <span
                        className={cn(
                          "text-xs sm:text-sm truncate transition-colors",
                          !n.is_read
                            ? "font-bold text-foreground"
                            : "font-normal text-muted-foreground group-hover:text-cyan-glow",
                        )}
                      >
                        {n.title}
                      </span>
                      {formattedDate && (
                        <span className="font-mono text-[10px] sm:text-[11px] text-muted-foreground whitespace-nowrap shrink-0">
                          {formattedDate}
                        </span>
                      )}
                    </div>

                    {displayBody && (
                      <p className="text-xs text-muted-foreground line-clamp-2 mt-0.5 font-normal">
                        {displayBody}
                      </p>
                    )}
                  </div>

                  {/* Punto indicador de no leída */}
                  {!n.is_read && (
                    <span
                      className="size-2 rounded-full bg-cyan-glow shrink-0 mt-1.5"
                      aria-hidden="true"
                    />
                  )}
                </button>
              );
            })
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
