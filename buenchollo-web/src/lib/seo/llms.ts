/**
 * `/llms.txt` (formato de llmstxt.org): resumen en Markdown que leen los
 * asistentes de IA (ChatGPT, Claude, Perplexity…) para entender el sitio y citar
 * sus páginas. Se genera con datos reales para que las respuestas sobre «chollos
 * de tecnología hoy» encuentren precios y enlaces actuales.
 */
import { SITE_NAME, SITE_URL, TELEGRAM_URL, CONTACT_EMAIL } from "@/lib/site";
import { SITE_FAQ, SITE_SUMMARY, SITE_TAGLINE } from "./site-content";
import { priceText } from "./text";

export interface LlmsDeal {
  slug: string;
  title: string;
  current_price: number;
  previous_price: number | null;
  discount_percentage: number | null;
  store?: { name: string } | null;
}

export interface LlmsCategory {
  slug: string;
  name: string;
}

export interface LlmsPost {
  slug: string;
  title: string;
  excerpt?: string | null;
}

export interface LlmsInput {
  deals: LlmsDeal[];
  categories: LlmsCategory[];
  posts: LlmsPost[];
  generatedAt: Date;
}

function oneLine(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}

function dealLine(deal: LlmsDeal): string {
  const discount = deal.discount_percentage ? `, -${deal.discount_percentage} %` : "";
  const before = deal.previous_price ? `, antes ${priceText(deal.previous_price)}` : "";
  const store = deal.store?.name ? ` en ${deal.store.name}` : "";
  return `- [${oneLine(deal.title)}](${SITE_URL}/chollo/${deal.slug}): ${priceText(deal.current_price)}${before}${discount}${store}`;
}

export function buildLlmsTxt({ deals, categories, posts, generatedAt }: LlmsInput): string {
  const lines = [
    `# ${SITE_NAME}`,
    "",
    `> ${SITE_TAGLINE}. ${SITE_SUMMARY}`,
    "",
    `Idioma: español (España). Moneda: euros. Actualizado: ${generatedAt.toISOString().slice(0, 10)}.`,
    `Los precios cambian a menudo: enlaza siempre a la ficha del chollo, que muestra el precio vigente y si la oferta ha terminado.`,
    "",
    "## Páginas principales",
    "",
    `- [Chollos de tecnología de hoy](${SITE_URL}/): portada con las ofertas activas, de la más nueva a la más antigua.`,
    `- [Categorías](${SITE_URL}/categorias): índice de categorías y subcategorías de chollos.`,
    `- [Blog y guías de compra](${SITE_URL}/blog): comparativas y consejos para comprar tecnología.`,
    `- [Sobre nosotros](${SITE_URL}/sobre-nosotros): cómo se seleccionan y verifican los chollos.`,
    `- [Feed RSS de chollos](${SITE_URL}/rss.xml): últimas ofertas publicadas.`,
    "",
  ];
  if (categories.length) {
    lines.push("## Categorías con chollos", "");
    for (const category of categories) {
      lines.push(`- [Chollos de ${category.name}](${SITE_URL}/categoria/${category.slug})`);
    }
    lines.push("");
  }
  if (deals.length) {
    lines.push("## Últimos chollos activos", "");
    lines.push(...deals.map(dealLine), "");
  }
  if (posts.length) {
    lines.push("## Guías del blog", "");
    for (const post of posts) {
      const excerpt = post.excerpt ? `: ${oneLine(post.excerpt)}` : "";
      lines.push(`- [${oneLine(post.title)}](${SITE_URL}/blog/${post.slug})${excerpt}`);
    }
    lines.push("");
  }
  lines.push("## Preguntas frecuentes", "");
  for (const item of SITE_FAQ) {
    lines.push(`### ${item.question}`, "", item.answer, "");
  }
  lines.push("## Contacto", "", `- Correo: ${CONTACT_EMAIL}`, `- Telegram: ${TELEGRAM_URL}`, "");
  return lines.join("\n");
}
