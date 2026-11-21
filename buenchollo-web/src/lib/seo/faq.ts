/** SEO de /preguntas-frecuentes: las preguntas visibles y su `FAQPage`. */
import { withBrand, type PageSeo } from "./head";
import { breadcrumbSchema, collectionPageSchema, faqSchema } from "./schema";
import { SITE_FAQ } from "./site-content";

export const FAQ_PATH = "/preguntas-frecuentes";

export function faqPageSeo(): PageSeo {
  const description =
    "Respuestas sobre BuenChollo Tech: cómo verificamos los chollos, alertas y avisos, «Los chollos de la semana», precios y descuentos, y dónde se compra cada producto.";
  return {
    title: withBrand("Preguntas frecuentes"),
    description,
    path: FAQ_PATH,
    jsonLd: [
      collectionPageSchema("Preguntas frecuentes", FAQ_PATH, description),
      breadcrumbSchema([
        { name: "Inicio", path: "/" },
        { name: "Preguntas frecuentes", path: FAQ_PATH },
      ]),
      faqSchema(SITE_FAQ),
    ],
  };
}
