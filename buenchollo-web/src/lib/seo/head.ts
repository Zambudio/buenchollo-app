/**
 * Cabecera SEO común de cada página indexable: título, descripción, canonical,
 * robots, Open Graph, Twitter y datos estructurados (JSON-LD).
 *
 * Todas las rutas públicas la usan para que ninguna olvide una etiqueta. Las
 * etiquetas globales (charset, viewport, og:site_name, og:locale, twitter:card)
 * viven en `__root.tsx`; las de aquí las sobrescriben por nombre o propiedad.
 */
import { serializeJsonLd } from "@/lib/json-ld";
import { SITE_NAME, SITE_URL } from "@/lib/site";
import { clampDescription } from "./text";

export const DEFAULT_OG_IMAGE = `${SITE_URL}/og-image.png`;

/** Robots de las páginas indexables: fragmentos e imágenes grandes permitidos
 *  (los usan Google Discover y los resúmenes de buscadores con IA). */
export const ROBOTS_INDEX = "index, follow, max-image-preview:large, max-snippet:-1";
export const ROBOTS_NOINDEX = "noindex, follow";

type MetaTag =
  | { title: string }
  | { name: string; content: string }
  | { property: string; content: string };

export interface PageSeo {
  /** Título completo; usa `withBrand` para añadir la marca. */
  title: string;
  description: string;
  /** Ruta absoluta desde la raíz («/chollo/x») o URL completa. */
  path: string;
  image?: string | null;
  imageAlt?: string;
  type?: "website" | "article" | "product";
  noindex?: boolean;
  /** Nodos schema.org; se publican juntos en un `@graph`. */
  jsonLd?: object[];
  /** Etiquetas adicionales (p. ej. `article:published_time`). */
  extraMeta?: MetaTag[];
}

export function absoluteUrl(path: string): string {
  if (/^https?:\/\//.test(path)) return path;
  return `${SITE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

/** «Título | BuenChollo Tech», sin duplicar la marca. */
export function withBrand(title: string): string {
  return title.includes(SITE_NAME) ? title : `${title} | ${SITE_NAME}`;
}

export function pageHead(seo: PageSeo) {
  const url = absoluteUrl(seo.path);
  const description = clampDescription(seo.description);
  const image = seo.image ? absoluteUrl(seo.image) : DEFAULT_OG_IMAGE;
  const socialTitle = seo.title.replace(` | ${SITE_NAME}`, "");

  const meta: MetaTag[] = [
    { title: seo.title },
    { name: "description", content: description },
    { name: "robots", content: seo.noindex ? ROBOTS_NOINDEX : ROBOTS_INDEX },
    { property: "og:title", content: socialTitle },
    { property: "og:description", content: description },
    { property: "og:url", content: url },
    { property: "og:type", content: seo.type ?? "website" },
    { property: "og:image", content: image },
    { property: "og:image:alt", content: seo.imageAlt ?? socialTitle },
    { name: "twitter:title", content: socialTitle },
    { name: "twitter:description", content: description },
    { name: "twitter:image", content: image },
    ...(seo.extraMeta ?? []),
  ];

  return {
    meta,
    links: [{ rel: "canonical", href: url }],
    scripts: seo.jsonLd?.length
      ? [
          {
            type: "application/ld+json",
            children: serializeJsonLd({ "@context": "https://schema.org", "@graph": seo.jsonLd }),
          },
        ]
      : [],
  };
}

/** Páginas privadas o de utilidad: fuera del índice, sin canonical ni JSON-LD. */
export function privatePageHead(title: string, description: string) {
  return {
    meta: [
      { title: withBrand(title) },
      { name: "description", content: clampDescription(description) },
      { name: "robots", content: "noindex, nofollow" },
    ],
  };
}
