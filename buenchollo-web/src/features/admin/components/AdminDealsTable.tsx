/** Tabla del listado admin de chollos. Presentación pura (TD-03). */
import { Link } from "@tanstack/react-router";
import { Edit3, Send, Trash2 } from "lucide-react";
import type { DealDetailData } from "@/services/api/deals";
import { formatPrice, formatRelativeTime } from "@/lib/format";

interface Props {
  readonly deals: DealDetailData[];
  readonly onEdit: (d: DealDetailData) => void;
  readonly onTelegram: (d: DealDetailData) => void;
  readonly onRemove: (id: string) => void;
}

export function AdminDealsTable({ deals, onEdit, onTelegram, onRemove }: Props) {
  return (
    <div className="bg-surface-800 border border-surface-700 overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="border-b border-surface-700 font-mono text-xs uppercase text-muted-foreground">
          <tr>
            <th className="p-3 w-14">
              <span className="sr-only">Imagen</span>
            </th>
            <th className="text-left p-3">Título</th>
            <th className="text-left p-3">Tienda</th>
            <th className="text-right p-3">Precio</th>
            <th className="text-left p-3">Estado</th>
            <th className="text-left p-3">Fecha</th>
            <th className="p-3">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {deals.map((d) => {
            const stCls =
              d.status === "active"
                ? "bg-cyan-glow/15 text-cyan-glow"
                : d.status === "scheduled"
                  ? "bg-amber-500/15 text-amber-400"
                  : d.status === "expired"
                    ? "bg-alert-red/15 text-alert-red"
                    : "bg-surface-700 text-muted-foreground";
            return (
              <tr key={d.id} className="border-b border-surface-700/50 hover:bg-surface-700/30">
                <td className="p-2">
                  {d.image_url || (d.images && d.images[0]) ? (
                    <img
                      src={d.images?.[0] ?? d.image_url ?? ""}
                      alt=""
                      className="w-10 h-10 object-contain bg-white rounded-sm shrink-0"
                    />
                  ) : (
                    <div className="w-10 h-10 bg-surface-700 rounded-sm" />
                  )}
                </td>
                <td className="p-3">
                  <Link
                    to="/chollo/$slug"
                    params={{ slug: d.slug }}
                    className="hover:text-cyan-glow"
                  >
                    {d.title}
                  </Link>
                </td>
                <td className="p-3 text-muted-foreground font-mono text-xs">
                  {d.store?.name ?? "—"}
                </td>
                <td className="p-3 text-right font-mono text-cyan-glow">
                  {formatPrice(d.current_price)}
                </td>
                <td className="p-3">
                  <span className={`font-mono text-[10px] uppercase px-2 py-1 ${stCls}`}>
                    {d.status}
                  </span>
                </td>
                <td className="p-3 text-muted-foreground font-mono text-xs">
                  {d.status === "scheduled" && d.scheduled_for ? (
                    <>📅 {new Date(d.scheduled_for).toLocaleString("es-ES")}</>
                  ) : d.expires_at ? (
                    <>⏱ {new Date(d.expires_at).toLocaleString("es-ES")}</>
                  ) : (
                    formatRelativeTime(d.created_at ?? d.published_at ?? "")
                  )}
                </td>
                <td className="p-3 flex gap-1">
                  <button
                    type="button"
                    onClick={() => onEdit(d)}
                    className="p-1.5 hover:text-cyan-glow"
                    title="Editar"
                  >
                    <Edit3 className="size-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => onTelegram(d)}
                    className="p-1.5 hover:text-cyan-glow"
                    title="Publicar en Telegram"
                  >
                    <Send className="size-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => onRemove(d.id)}
                    className="p-1.5 hover:text-alert-red"
                    title="Eliminar"
                  >
                    <Trash2 className="size-4" />
                  </button>
                </td>
              </tr>
            );
          })}
          {deals.length === 0 && (
            <tr>
              <td colSpan={7} className="p-6 text-center text-muted-foreground font-mono text-xs">
                SIN_RESULTADOS
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
