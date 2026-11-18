/**
 * Nodos schema.org reutilizables. Se enlazan por `@id` para que buscadores y
 * asistentes de IA reconozcan una única entidad «BuenChollo Tech» en todo el
 * sitio (E-E-A-T: quién publica, desde dónde y cómo contactar).
 */
import { CONTACT_EMAIL, SITE_NAME, SITE_URL, TELEGRAM_URL } from "@/lib/site";
import { absoluteUrl } from "./head";

export const ORGANIZATION_ID = `${SITE_URL}/#organization`;
export const WEBSITE_ID = `${SITE_URL}/#website`;

export function organizationSchema() {
  return {
    "@type": "Organization",
    "@id": ORGANIZATION_ID,
    name: SITE_NAME,
    url: `${SITE_URL}/`,
    logo: { "@type": "ImageObject", url: `${SITE_URL}/logo-512.png`, width: 512, height: 512 },
    email: CONTACT_EMAIL,
    sameAs: [TELEGRAM_URL],
    areaServed: "ES",
    knowsAbout: [
      "chollos de tecnología",
      "ofertas de electrónica",
      "descuentos en Amazon",
      "comparativas de precios",
    ],
  };
}

export function websiteSchema() {
  return {
    "@type": "WebSite",
    "@id": WEBSITE_ID,
    url: `${SITE_URL}/`,
    name: SITE_NAME,
    description: "Chollos y ofertas de tecnología en España, verificados y actualizados a diario.",
    inLanguage: "es-ES",
    publisher: { "@id": ORGANIZATION_ID },
    potentialAction: {
      "@type": "SearchAction",
      target: { "@type": "EntryPoint", urlTemplate: `${SITE_URL}/explorar?q={search_term_string}` },
      "query-input": "required name=search_term_string",
    },
  };
}

export interface Crumb {
  name: string;
  path: string;
}

export function breadcrumbSchema(crumbs: Crumb[]) {
  return {
    "@type": "BreadcrumbList",
    itemListElement: crumbs.map((crumb, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: crumb.name,
      item: absoluteUrl(crumb.path),
    })),
  };
}

export interface ListedDeal {
  slug: string;
  title: string;
}

/** Lista de chollos de una página de listado (portada, categoría). */
export function dealListSchema(name: string, deals: ListedDeal[]) {
  return {
    "@type": "ItemList",
    name,
    numberOfItems: deals.length,
    itemListElement: deals.map((deal, index) => ({
      "@type": "ListItem",
      position: index + 1,
      url: absoluteUrl(`/chollo/${deal.slug}`),
      name: deal.title,
    })),
  };
}

export function collectionPageSchema(name: string, path: string, description: string) {
  return {
    "@type": "CollectionPage",
    "@id": `${absoluteUrl(path)}#webpage`,
    name,
    url: absoluteUrl(path),
    description,
    inLanguage: "es-ES",
    isPartOf: { "@id": WEBSITE_ID },
    publisher: { "@id": ORGANIZATION_ID },
  };
}

export interface FaqItem {
  question: string;
  answer: string;
}

/** Solo para preguntas que se muestran tal cual en la página. */
export function faqSchema(items: FaqItem[]) {
  return {
    "@type": "FAQPage",
    mainEntity: items.map((item) => ({
      "@type": "Question",
      name: item.question,
      acceptedAnswer: { "@type": "Answer", text: item.answer },
    })),
  };
}
