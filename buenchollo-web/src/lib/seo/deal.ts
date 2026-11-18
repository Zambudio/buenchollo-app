/**
 * SEO de la ficha de un chollo (`/chollo/$slug`).
 *
 * - Oferta activa: título orientado a búsquedas «chollo + producto» con precio y
 *   descuento, `Product` + `Offer` para resultados enriquecidos.
 * - Oferta terminada: la página muestra el producto sin precio, así que ni el
 *   título ni el JSON-LD lo anuncian (Google penaliza la discrepancia de precio).
 * - Borrador o programado: fuera del índice.
 */
import type { DealDetailData } from "@/services/api/deals";
import { calculateDiscount } from "@/lib/format";
import { isInStock } from "@/lib/offer-status";
import { absoluteUrl, withBrand, type PageSeo } from "./head";
import { breadcrumbSchema, ORGANIZATION_ID, type Crumb } from "./schema";
import { clampText, priceText } from "./text";

/** Longitud del nombre del producto en el título, para que precio y marca quepan. */
const TITLE_PRODUCT_MAX = 58;

export function dealPath(slug: string): string {
  return `/chollo/${slug}`;
}

export function isOfferLive(deal: Pick<DealDetailData, "status">): boolean {
  return deal.status === "active";
}

function dealCrumbs(deal: DealDetailData): Crumb[] {
  const crumbs: Crumb[] = [{ name: "Inicio", path: "/" }];
  if (deal.category) {
    crumbs.push({ name: deal.category.name, path: `/categoria/${deal.category.slug}` });
  }
  if (deal.subcategory) {
    crumbs.push({ name: deal.subcategory.name, path: `/categoria/${deal.subcategory.slug}` });
  }
  crumbs.push({ name: deal.title, path: dealPath(deal.slug) });
  return crumbs;
}

function dealImages(deal: DealDetailData): string[] {
  const images = deal.images?.length ? deal.images : deal.image_url ? [deal.image_url] : [];
  return images.slice(0, 5);
}

function futureDate(value: string | null | undefined, now: Date): string | undefined {
  if (!value) return undefined;
  const date = new Date(value);
  return date.getTime() > now.getTime() ? date.toISOString().slice(0, 10) : undefined;
}

function productSchema(deal: DealDetailData, now: Date) {
  const url = absoluteUrl(dealPath(deal.slug));
  const images = dealImages(deal);
  return {
    "@type": "Product",
    "@id": `${url}#product`,
    name: deal.title,
    description: clampText(deal.short_description || deal.description || deal.title, 500),
    image: images.length ? images : undefined,
    brand: deal.brand ? { "@type": "Brand", name: deal.brand } : undefined,
    category: deal.subcategory?.name ?? deal.category?.name ?? undefined,
    sku: deal.external_id || deal.id,
    url,
    offers: {
      "@type": "Offer",
      url,
      price: deal.current_price,
      priceCurrency: "EUR",
      priceValidUntil: futureDate(deal.expires_at, now),
      availability: isInStock(deal)
        ? "https://schema.org/InStock"
        : "https://schema.org/OutOfStock",
      itemCondition: "https://schema.org/NewCondition",
      seller: deal.store?.name ? { "@type": "Organization", name: deal.store.name } : undefined,
      offeredBy: { "@id": ORGANIZATION_ID },
    },
  };
}

function liveTitle(deal: DealDetailData, discount: number | null): string {
  const product = clampText(deal.title, TITLE_PRODUCT_MAX);
  const off = discount ? ` (-${discount} %)` : "";
  return withBrand(`Chollo ${product} por ${priceText(deal.current_price)}${off}`);
}

function liveDescription(deal: DealDetailData, discount: number | null): string {
  const before =
    deal.previous_price && discount
      ? ` (antes ${priceText(deal.previous_price)}, -${discount} %)`
      : "";
  const store = deal.store?.name ? ` en ${deal.store.name}` : "";
  const summary = deal.short_description ? ` ${clampText(deal.short_description, 90)}.` : "";
  return `${deal.title} por ${priceText(deal.current_price)}${before}${store}.${summary} Precio verificado por BuenChollo Tech.`;
}

export function dealPageSeo(deal: DealDetailData, now: Date = new Date()): PageSeo {
  const images = dealImages(deal);
  const crumbs = breadcrumbSchema(dealCrumbs(deal));
  const base = { path: dealPath(deal.slug), image: images[0], imageAlt: deal.title };

  if (deal.status === "draft" || deal.status === "scheduled") {
    return { ...base, title: withBrand(deal.title), description: deal.title, noindex: true };
  }

  if (!isOfferLive(deal)) {
    const product = clampText(deal.title, TITLE_PRODUCT_MAX);
    return {
      ...base,
      title: withBrand(`${product}: oferta terminada`),
      description: `La oferta de ${deal.title} ha terminado. Consulta chollos parecidos y crea una alerta gratuita para saber cuándo vuelve a bajar de precio.`,
      jsonLd: [crumbs],
    };
  }

  const discount =
    deal.discount_percentage ?? calculateDiscount(deal.current_price, deal.previous_price);
  return {
    ...base,
    title: liveTitle(deal, discount),
    description: liveDescription(deal, discount),
    type: "product",
    jsonLd: [productSchema(deal, now), crumbs],
    extraMeta: [
      { property: "product:price:amount", content: String(deal.current_price) },
      { property: "product:price:currency", content: "EUR" },
      { property: "product:availability", content: isInStock(deal) ? "in stock" : "out of stock" },
      ...(deal.published_at
        ? [{ property: "article:published_time", content: deal.published_at }]
        : []),
    ],
  };
}
