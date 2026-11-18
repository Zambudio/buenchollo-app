/** SEO de la portada: la página que debe posicionar «chollos de tecnología». */
import { withBrand, type PageSeo } from "./head";
import {
  dealListSchema,
  faqSchema,
  organizationSchema,
  websiteSchema,
  type ListedDeal,
} from "./schema";
import { SITE_FAQ } from "./site-content";

export const HOME_H1 = "Chollos de tecnología hoy: ofertas y descuentos verificados";

export interface HomeSeoInput {
  page: number;
  deals: ListedDeal[];
}

/**
 * Las páginas 2, 3… son URLs propias (`/?page=N`) con su canonical, para que los
 * buscadores sigan la paginación y descubran chollos antiguos. Los cambios de
 * orden (`?sort=`) apuntan al canonical sin orden: son la misma lista.
 */
export function homeSeo({ page, deals }: HomeSeoInput): PageSeo {
  const first = page <= 1;
  return {
    title: first
      ? withBrand("Chollos de tecnología hoy: las mejores ofertas y descuentos")
      : withBrand(`Chollos de tecnología: página ${page}`),
    description:
      "Los mejores chollos de tecnología de hoy en España: móviles, portátiles, auriculares, televisores, gaming e informática con descuento. Ofertas verificadas a diario y alertas gratis.",
    path: first ? "/" : `/?page=${page}`,
    jsonLd: [
      organizationSchema(),
      websiteSchema(),
      ...(deals.length
        ? [
            dealListSchema(
              first ? "Chollos de tecnología de hoy" : `Chollos de tecnología, página ${page}`,
              deals,
            ),
          ]
        : []),
      ...(first ? [faqSchema(SITE_FAQ)] : []),
    ],
  };
}
