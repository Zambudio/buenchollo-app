import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight, Clock, Send } from "lucide-react";
import { Layout } from "@/components/layout/Layout";
import { DealCard } from "@/features/deals/components/DealCard";
import { CampaignCountdown } from "@/features/campaigns/CampaignCountdown";
import { dealsService } from "@/services/api/deals";
import { withFallback } from "@/lib/fallback";
import { BLACK_FRIDAY, campaignStatus, formatCampaignDate, lastDayOf } from "@/lib/campaigns";
import { pageHead } from "@/lib/seo/head";
import { campaignFaq, campaignPageSeo } from "@/lib/seo/campaign";
import { TELEGRAM_URL } from "@/lib/site";
import { SiteFaq } from "@/features/home/SiteFaq";

const PAGE_SIZE = 48;

export const Route = createFileRoute("/black-friday")({
  component: BlackFridayPage,
  loader: async () => {
    const page = await withFallback(
      dealsService.getPage({
        sort: "discount",
        min_discount: BLACK_FRIDAY.minDiscount,
        page: 1,
        page_size: PAGE_SIZE,
      }),
      { items: [], total_pages: 1, page: 1, page_size: PAGE_SIZE, total: 0 },
      "Error cargando chollos de Black Friday",
    );
    // La hora se fija en el loader para que servidor y cliente pinten la misma fase.
    return { deals: page.items, total: page.total, now: Date.now() };
  },
  head: ({ loaderData }) =>
    pageHead(
      campaignPageSeo(
        BLACK_FRIDAY,
        campaignStatus(BLACK_FRIDAY, new Date(loaderData?.now ?? Date.now())),
        loaderData?.deals ?? [],
      ),
    ),
});

function BlackFridayPage() {
  const { deals, total, now } = Route.useLoaderData();
  const status = campaignStatus(BLACK_FRIDAY, new Date(now));
  const { edition, phase, target } = status;
  const faq = campaignFaq(BLACK_FRIDAY, status);
  const lastDay = lastDayOf(edition);

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <header className="campaign-hero campaign-landing-header">
          <div className="campaign-hero-copy">
            <span className="eyebrow">
              {phase === "live"
                ? "Ya ha empezado"
                : phase === "upcoming"
                  ? `Empieza el ${formatCampaignDate(edition.start)}`
                  : "Edición terminada"}
            </span>
            <h1>
              {BLACK_FRIDAY.name} {edition.year}
              <br />
              <span>chollos de tecnología verificados</span>
            </h1>
            <p>
              Ofertas de tecnología con al menos un {BLACK_FRIDAY.minDiscount} % de descuento,
              ordenadas de mayor a menor. Revisamos cada chollo antes de publicarlo y comprobamos su
              precio y stock a diario.
            </p>
            <a
              href={TELEGRAM_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="campaign-hero-cta"
            >
              <Send size={17} aria-hidden="true" /> Avisos al momento en Telegram
            </a>
          </div>
          {target && (
            <div className="campaign-hero-countdown">
              <span className="campaign-hero-countdown-label">
                <Clock size={15} aria-hidden="true" />{" "}
                {phase === "live" ? "Termina en" : "Empieza en"}
              </span>
              <CampaignCountdown
                target={target}
                fallback={formatCampaignDate(phase === "live" ? lastDay : edition.start)}
                className="campaign-hero-countdown-value"
              />
            </div>
          )}
        </header>

        <h2 className="feed-section-title">
          {total > 0
            ? `${total} chollos con al menos un ${BLACK_FRIDAY.minDiscount} % de descuento`
            : "Chollos de Black Friday"}
        </h2>
        {deals.length === 0 ? (
          <p className="py-10 text-center font-mono text-sm text-muted-foreground">
            Ahora mismo no hay chollos con al menos un {BLACK_FRIDAY.minDiscount} % de descuento.
            Únete al canal de Telegram y te avisamos en cuanto salgan.
          </p>
        ) : (
          <div className="deal-feed-grid">
            {deals.map((d, index) => (
              <DealCard key={d.id} deal={d} imageLoading={index < 3 ? "eager" : "lazy"} />
            ))}
          </div>
        )}
        {total > deals.length && (
          <p className="mt-8 text-center">
            <Link
              to="/explorar"
              search={{ sort: "discount", disc: BLACK_FRIDAY.minDiscount }}
              className="campaign-more-link"
            >
              Ver los {total} chollos con descuento <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </p>
        )}

        <SiteFaq items={faq} />
      </div>
    </Layout>
  );
}
