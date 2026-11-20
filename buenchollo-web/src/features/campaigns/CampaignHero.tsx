import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import type { ReactNode } from "react";
import { formatCampaignDate, lastDayOf, type Campaign, type CampaignStatus } from "@/lib/campaigns";
import { CampaignCountdown } from "./CampaignCountdown";

/**
 * Rótulo de neón de una campaña estacional: portada (h2, enlace a la landing)
 * y cabecera de la landing (h1, CTA propio). Siempre oscuro, también en el
 * tema claro: un neón solo luce de noche.
 */
export function CampaignHero({
  campaign,
  status,
  headingLevel = "h2",
  cta,
}: {
  campaign: Campaign;
  status: CampaignStatus;
  headingLevel?: "h1" | "h2";
  cta?: ReactNode;
}) {
  const { edition, phase, target } = status;
  const live = phase === "live";
  const Heading = headingLevel;
  const eyebrow = live
    ? `En directo hasta el ${formatCampaignDate(lastDayOf(edition))}`
    : phase === "upcoming"
      ? `Se enciende el ${formatCampaignDate(edition.start)}`
      : "Edición terminada";

  return (
    <section className="neon-sign" aria-labelledby="neon-sign-heading">
      <div className="neon-sign-copy">
        <p className={`neon-sign-eyebrow${live ? " is-live" : ""}`}>
          <span className="neon-sign-dot" aria-hidden="true" />
          {eyebrow}
        </p>
        <Heading id="neon-sign-heading" className="neon-sign-title">
          <span className="neon-sign-wordmark">{campaign.name}</span>
          <span className="neon-sign-year">{edition.year} · chollos tech verificados</span>
        </Heading>
        <p className="neon-sign-text">
          Tecnología con un {campaign.minDiscount} % de descuento o más, con el precio comprobado
          cada día.
        </p>
        {cta ?? (
          <Link to="/black-friday" className="neon-sign-cta">
            Ver chollos de {campaign.name} <ArrowRight size={18} aria-hidden="true" />
          </Link>
        )}
      </div>
      {target && (
        <div className="neon-sign-clock">
          <p className="neon-sign-clock-label">{live ? "Se apaga en" : "Se enciende en"}</p>
          <CampaignCountdown
            target={target}
            fallback={formatCampaignDate(live ? lastDayOf(edition) : edition.start)}
          />
        </div>
      )}
    </section>
  );
}
