/** SEO de las landings de campaña (`/black-friday`). La URL no lleva año: se
 *  reutiliza cada edición para acumular autoridad; el año va en el título. */
import type { Campaign, CampaignStatus } from "@/lib/campaigns";
import { formatCampaignDate } from "@/lib/campaigns";
import { withBrand, type PageSeo } from "./head";
import {
  breadcrumbSchema,
  collectionPageSchema,
  dealListSchema,
  faqSchema,
  type FaqItem,
  type ListedDeal,
} from "./schema";

export function campaignFaq(campaign: Campaign, status: CampaignStatus): FaqItem[] {
  const { edition } = status;
  const lastDay = formatCampaignDate(new Date(new Date(edition.end).getTime() - 1).toISOString());
  return [
    {
      question: `¿Cuándo es el ${campaign.name} ${edition.year}?`,
      answer: `El ${campaign.name} ${edition.year} es el ${formatCampaignDate(edition.start)}. Muchas tiendas adelantan ofertas durante la semana anterior y las alargan hasta el Cyber Monday (${lastDay}).`,
    },
    {
      question: "¿Qué chollos aparecen en esta página?",
      answer: `Los chollos de tecnología activos con al menos un ${campaign.minDiscount} % de descuento sobre el precio de referencia de la tienda, ordenados de mayor a menor descuento. Cada oferta se revisa antes de publicarse y una comprobación automática diaria vigila el precio y el stock.`,
    },
    {
      question: "¿Cómo me entero de los mejores chollos sin estar pendiente?",
      answer:
        "Únete al canal de Telegram de BuenChollo Tech, donde publicamos las mejores ofertas en cuanto salen, o crea una alerta de precio con tu cuenta gratuita.",
    },
  ];
}

export function campaignPageSeo(
  campaign: Campaign,
  status: CampaignStatus,
  deals: ListedDeal[],
): PageSeo {
  const path = `/${campaign.slug}`;
  const name = `${campaign.name} ${status.edition.year}`;
  const description = `Chollos de tecnología del ${name}: móviles, portátiles, auriculares, televisores y gaming con al menos un ${campaign.minDiscount} % de descuento, verificados a diario.`;
  const listName = `Chollos de ${name}`;
  return {
    title: withBrand(`${name}: chollos de tecnología verificados`),
    description,
    path,
    jsonLd: [
      collectionPageSchema(listName, path, description),
      breadcrumbSchema([
        { name: "Inicio", path: "/" },
        { name: campaign.name, path },
      ]),
      ...(deals.length > 0 ? [dealListSchema(listName, deals)] : []),
      faqSchema(campaignFaq(campaign, status)),
    ],
  };
}
