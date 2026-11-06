/** Motivos de fin de oferta en los que el producto sigue a la venta en la tienda. */
const STILL_ON_SALE = new Set(["price_increase", "no_longer_deal"]);

/**
 * Disponibilidad para schema.org / Open Graph. Con el catálogo permanente un
 * chollo sin oferta puede seguir a la venta (solo subió de precio); agotado,
 * retirado o caducado por fecha se anuncia como no disponible.
 */
export function isInStock(deal: { status: string; offer_end_reason?: string | null }): boolean {
  if (deal.status !== "expired") return true;
  return STILL_ON_SALE.has(deal.offer_end_reason ?? "");
}
