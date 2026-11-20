/**
 * Campañas estacionales (Black Friday, y en el futuro Prime Day, Días sin IVA…).
 *
 * Cada campaña tiene una URL fija que se reutiliza todos los años para que
 * acumule autoridad SEO; solo se añaden las fechas de cada edición. Las fechas
 * van con la zona horaria de Madrid explícita.
 */

export interface CampaignEdition {
  year: number;
  /** Desde cuándo se anuncia en el hero de portada. */
  promoteFrom: string;
  /** Inicio del evento. */
  start: string;
  /** Fin del evento (exclusivo): pasado este instante deja de anunciarse. */
  end: string;
}

export interface Campaign {
  slug: string;
  name: string;
  /** Descuento mínimo (%) de los chollos que se listan en la landing. */
  minDiscount: number;
  editions: CampaignEdition[];
}

export const BLACK_FRIDAY: Campaign = {
  slug: "black-friday",
  name: "Black Friday",
  minDiscount: 20,
  editions: [
    {
      year: 2026,
      promoteFrom: "2026-11-01T00:00:00+01:00",
      // Viernes 27 de noviembre; se alarga hasta el final del Cyber Monday (30).
      start: "2026-11-27T00:00:00+01:00",
      end: "2026-12-01T00:00:00+01:00",
    },
  ],
};

/** `end` es exclusivo (medianoche del día siguiente): el último día del evento es el anterior. */
export function lastDayOf(edition: CampaignEdition): string {
  return new Date(new Date(edition.end).getTime() - 1).toISOString();
}

export type CampaignPhase = "upcoming" | "live" | "ended";

export interface CampaignStatus {
  edition: CampaignEdition;
  phase: CampaignPhase;
  /** Instante al que apunta la cuenta atrás (inicio si aún no ha empezado, fin si está en curso). */
  target: Date | null;
  /** Si debe ocupar el hero de portada ahora mismo. */
  promoted: boolean;
}

const ms = (iso: string) => new Date(iso).getTime();

/** Edición vigente: la primera que aún no ha terminado o, si todas pasaron, la última. */
export function campaignStatus(campaign: Campaign, now: Date = new Date()): CampaignStatus {
  const t = now.getTime();
  const sorted = [...campaign.editions].sort((a, b) => ms(a.start) - ms(b.start));
  const edition = sorted.find((e) => t < ms(e.end)) ?? sorted.at(-1);
  if (!edition) throw new Error(`La campaña ${campaign.slug} no tiene ediciones`);
  const phase: CampaignPhase =
    t < ms(edition.start) ? "upcoming" : t < ms(edition.end) ? "live" : "ended";
  return {
    edition,
    phase,
    target:
      phase === "upcoming"
        ? new Date(edition.start)
        : phase === "live"
          ? new Date(edition.end)
          : null,
    promoted: phase !== "ended" && t >= ms(edition.promoteFrom),
  };
}

export interface Countdown {
  days: number;
  hours: number;
  minutes: number;
}

export function countdownTo(target: Date, now: Date = new Date()): Countdown {
  const totalMinutes = Math.max(0, Math.floor((target.getTime() - now.getTime()) / 60_000));
  return {
    days: Math.floor(totalMinutes / 1440),
    hours: Math.floor((totalMinutes % 1440) / 60),
    minutes: totalMinutes % 60,
  };
}

/** «6 d 7 h 12 min», omitiendo los días cuando ya no quedan. */
export function formatCountdown({ days, hours, minutes }: Countdown): string {
  return days > 0 ? `${days} d ${hours} h ${minutes} min` : `${hours} h ${minutes} min`;
}

/** «viernes 27 de noviembre», en hora de Madrid. */
export function formatCampaignDate(iso: string): string {
  return new Intl.DateTimeFormat("es-ES", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: "Europe/Madrid",
  })
    .format(new Date(iso))
    .replace(",", "");
}
