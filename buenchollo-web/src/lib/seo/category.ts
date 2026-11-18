/**
 * SEO de las páginas de categoría (`/categoria/$slug`), las que deben posicionar
 * búsquedas como «chollos de auriculares» u «ofertas de portátiles».
 *
 * Cada categoría principal tiene un texto propio y útil (qué mirar antes de
 * comprar); las subcategorías usan una plantilla con su nombre. Una categoría
 * sin chollos ni productos destacados queda fuera del índice para no publicar
 * páginas vacías (contenido escaso).
 */
import { withBrand, type PageSeo } from "./head";
import {
  breadcrumbSchema,
  collectionPageSchema,
  dealListSchema,
  type Crumb,
  type ListedDeal,
} from "./schema";

/** Introducción visible y meta description de las categorías principales. */
export const CATEGORY_INTROS: Record<string, string> = {
  informatica:
    "Portátiles, monitores, mini PC y accesorios de oficina con descuento. Revisamos a diario el precio y el stock de cada oferta para que solo veas descuentos vigentes.",
  "componentes-pc":
    "Procesadores, tarjetas gráficas, placas base, memoria RAM y fuentes de alimentación en oferta. Ideal para montar o actualizar tu PC sin pagar de más.",
  almacenamiento:
    "Discos SSD, discos duros, tarjetas de memoria y memorias USB rebajados. Fíjate en la capacidad real, la velocidad de lectura y la garantía del fabricante.",
  perifericos:
    "Teclados, ratones, webcams, alfombrillas y accesorios para el escritorio con descuento, tanto para trabajar como para jugar.",
  audio:
    "Auriculares inalámbricos, cascos con cancelación de ruido, barras de sonido y altavoces bluetooth en oferta, de marcas como Sony, JBL, Apple o Xiaomi.",
  "gaming-y-consolas":
    "Consolas, mandos, juegos y accesorios gaming con descuento. Revisamos el precio para avisarte cuando una rebaja es de verdad un chollo.",
  "smartphones-y-tablets":
    "Móviles, tablets y accesorios rebajados. Comprueba la versión (global o española), la memoria y las bandas de red antes de comprar.",
  "tv-e-imagen":
    "Televisores, proyectores y dispositivos de streaming en oferta. Compara tamaño, panel (OLED, QLED o LED) y frecuencia de refresco antes de decidir.",
  "fotografia-y-video":
    "Cámaras, objetivos, cámaras de acción, estabilizadores y drones con descuento para foto y vídeo.",
  redes:
    "Routers wifi, sistemas mesh, repetidores, switches y adaptadores de red en oferta para mejorar la conexión de casa o de la oficina.",
  domotica:
    "Enchufes inteligentes, bombillas, cámaras de seguridad, robots aspirador y asistentes de voz rebajados para automatizar tu casa.",
  wearables:
    "Relojes inteligentes, pulseras de actividad y otros wearables con descuento. Fíjate en la autonomía y en la compatibilidad con tu móvil.",
  energia:
    "Baterías externas, cargadores rápidos, cables y estaciones de energía portátiles en oferta.",
};

export function categoryIntro(slug: string, name: string, parentSlug?: string | null): string {
  return (
    CATEGORY_INTROS[slug] ??
    `Chollos y ofertas de ${name}${parentSlug ? "" : " de tecnología"} seleccionados y verificados a diario. Comprobamos el precio y el stock para que solo veas descuentos reales.`
  );
}

export interface CategorySeoInput {
  slug: string;
  name: string;
  parent?: { slug: string; name: string } | null;
  deals: ListedDeal[];
  topCount: number;
}

export function categoryPageSeo(input: CategorySeoInput): PageSeo {
  const { slug, name, parent, deals, topCount } = input;
  const path = `/categoria/${slug}`;
  const intro = categoryIntro(slug, name, parent?.slug);
  const count = deals.length;
  const description =
    count > 0
      ? `${count} chollos de ${name} activos ahora. ${intro}`
      : `Ofertas de ${name}: ${intro}`;
  const crumbs: Crumb[] = [
    { name: "Inicio", path: "/" },
    { name: "Categorías", path: "/categorias" },
    ...(parent ? [{ name: parent.name, path: `/categoria/${parent.slug}` }] : []),
    { name, path },
  ];
  const listName = `Chollos de ${name}`;
  return {
    title: withBrand(`Chollos de ${name} hoy: ofertas y descuentos`),
    description,
    path,
    noindex: count === 0 && topCount === 0,
    jsonLd: [
      collectionPageSchema(listName, path, description),
      breadcrumbSchema(crumbs),
      ...(count > 0 ? [dealListSchema(listName, deals)] : []),
    ],
  };
}
