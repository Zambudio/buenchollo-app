import { AlertCircle } from "lucide-react";
import { formatPrice } from "@/lib/format";

/** Más allá de esto un precio deja de presentarse como actual (Amazon exige ≤ 24 h). */
const FRESH_HOURS = 24;

const END_REASON_LABEL: Record<string, string> = {
  price_increase: "Ha subido de precio",
  no_longer_deal: "Ya no está rebajado",
  out_of_stock: "Agotado",
  not_found: "Ya no está en la tienda",
};

interface OfferStatusNoticeProps {
  status: string;
  offerEndReason: string | null | undefined;
  currentPrice: number;
  lastPriceCheckAt: string | null | undefined;
  storeName?: string | null;
  /** Inyectable para tests; por defecto, el momento del render. */
  now?: Date;
  /** Clases extra para la línea de frescura de una oferta activa. */
  className?: string;
}

function hoursSince(date: string, now: Date): number {
  return (now.getTime() - new Date(date).getTime()) / 3_600_000;
}

function checkedAgo(hours: number): string {
  if (hours < 1) return "hace menos de 1 h";
  if (hours < 24) return `hace ${Math.floor(hours)} h`;
  const days = Math.floor(hours / 24);
  return `hace ${days} ${days === 1 ? "día" : "días"}`;
}

/**
 * Estado de la oferta en la ficha del catálogo permanente: el chollo ya no se
 * borra, así que la ficha explica si ahora mismo está en oferta y de cuándo es
 * el precio que mostramos.
 */
export function OfferStatusNotice({
  status,
  offerEndReason,
  currentPrice,
  lastPriceCheckAt,
  storeName,
  now = new Date(),
  className = "",
}: OfferStatusNoticeProps) {
  const hours = lastPriceCheckAt ? hoursSince(lastPriceCheckAt, now) : null;
  const fresh = hours !== null && hours <= FRESH_HOURS;

  if (status === "active") {
    if (hours === null) return null;
    return (
      <p className={`mb-3 font-mono text-xs text-muted-foreground ${className}`.trim()}>
        {fresh
          ? `Precio comprobado ${checkedAgo(hours)}`
          : `Precio de ${checkedAgo(hours)}: puede haber cambiado`}
      </p>
    );
  }

  if (status !== "expired") return null;

  const reason = (offerEndReason && END_REASON_LABEL[offerEndReason]) || "La oferta ha terminado";
  const isAmazon = (storeName ?? "").toLowerCase().startsWith("amazon");

  return (
    <div
      role="status"
      className="mb-4 flex items-start gap-2 border border-alert-red/40 bg-alert-red/10 px-4 py-3 font-mono text-xs text-alert-red"
    >
      <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <div className="min-w-0 space-y-1">
        <p className="font-bold uppercase">Ahora mismo no está en oferta</p>
        <p>{reason}. Mantenemos la ficha y volverá a aparecer como chollo si baja de nuevo.</p>
        {fresh ? (
          <p>
            Precio actual: {formatPrice(currentPrice)} · comprobado {checkedAgo(hours)}
          </p>
        ) : (
          isAmazon && <p>Ver precio en Amazon</p>
        )}
      </div>
    </div>
  );
}
