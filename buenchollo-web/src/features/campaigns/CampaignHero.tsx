import { Link } from "@tanstack/react-router";
import { ArrowRight, Clock } from "lucide-react";
import { formatCampaignDate, lastDayOf, type Campaign, type CampaignStatus } from "@/lib/campaigns";
import { CampaignCountdown } from "./CampaignCountdown";

/** Hero de portada mientras una campaña estacional está anunciada o en curso. */
export function CampaignHero({ campaign, status }: { campaign: Campaign; status: CampaignStatus }) {
  const { edition, phase, target } = status;
  const live = phase === "live";
  return (
    <section className="campaign-hero" aria-labelledby="campaign-hero-heading">
      <div className="campaign-hero-copy">
        <span className="eyebrow">
          {live ? "Ya ha empezado" : `Empieza el ${formatCampaignDate(edition.start)}`}
        </span>
        <h2 id="campaign-hero-heading">
          {campaign.name} {edition.year}
          <br />
          <span>chollos tech verificados.</span>
        </h2>
        <p>
          Reunimos las ofertas de tecnología con al menos un {campaign.minDiscount} % de descuento y
          comprobamos su precio a diario.
        </p>
        <Link to="/black-friday" className="campaign-hero-cta">
          Ver chollos de {campaign.name} <ArrowRight size={17} aria-hidden="true" />
        </Link>
      </div>
      {target && (
        <div className="campaign-hero-countdown">
          <span className="campaign-hero-countdown-label">
            <Clock size={15} aria-hidden="true" /> {live ? "Termina en" : "Empieza en"}
          </span>
          <CampaignCountdown
            target={target}
            fallback={formatCampaignDate(live ? lastDayOf(edition) : edition.start)}
            className="campaign-hero-countdown-value"
          />
        </div>
      )}
    </section>
  );
}
