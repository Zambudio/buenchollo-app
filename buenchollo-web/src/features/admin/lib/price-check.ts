/** Etiquetas y resumen de la revisión diaria de precios (catálogo permanente). */

export const TRANSITION_LABEL: Record<string, string> = {
  offer_ended: "Oferta terminada",
  reactivated: "Reactivada",
  purged: "Eliminada",
};

export const REASON_LABEL: Record<string, string> = {
  price_increase: "Subió de precio",
  no_longer_deal: "Ya no es oferta",
  out_of_stock: "Sin stock",
  not_found: "Ya no está en la tienda",
  expired_date: "Caducada por fecha",
  manual: "Terminada a mano",
  deal_again: "Vuelve a estar en oferta",
  listing_purged: "Tienda retirada del producto",
  product_purged: "Producto sin tiendas",
};

export function describeChange(transition: string, reason: string): string {
  return `${TRANSITION_LABEL[transition] ?? transition} · ${REASON_LABEL[reason] ?? reason}`;
}

const SUMMARY: [string, string, string][] = [
  ["offer_ended", "oferta terminada", "ofertas terminadas"],
  ["reactivated", "reactivada", "reactivadas"],
  ["purged", "eliminada", "eliminadas"],
];

export function summarizeTransitions(items: { transition: string }[]): string {
  const parts = SUMMARY.flatMap(([key, one, many]) => {
    const count = items.filter((item) => item.transition === key).length;
    return count ? [`${count} ${count === 1 ? one : many}`] : [];
  });
  return parts.length ? parts.join(" · ") : "Sin cambios";
}
