export function formatPrice(price: number | null | undefined): string {
  if (price == null) return "—";
  return new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: price % 1 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(price);
}

export function formatRelativeTime(date: string | Date | null | undefined): string {
  if (!date) return "—";
  const d = typeof date === "string" ? new Date(date) : date;
  if (!d || isNaN(d.getTime())) return "—";
  const seconds = Math.floor((Date.now() - d.getTime()) / 1000);
  if (seconds < 60) return "ahora";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours} h`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `hace ${days} d`;
  const months = Math.floor(days / 30);
  if (months < 12) return `hace ${months} mes${months > 1 ? "es" : ""}`;
  return d.toLocaleDateString("es-ES");
}

export function slugify(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .slice(0, 80);
}

/** Porcentaje de descuento entero entre dos precios. `null` si no hay precio
 *  anterior o el c\u00e1lculo no aplica (precio anterior <= actual, valores nulos). */
export function calculateDiscount(
  current: number | null | undefined,
  previous: number | null | undefined,
): number | null {
  if (!previous || !current || previous <= current) return null;
  return Math.round((1 - current / previous) * 100);
}

/** Convierte un ISO string (o equivalente) al formato que acepta
 *  <input type="datetime-local"> (YYYY-MM-DDTHH:mm, sin zona). */
export function toDatetimeLocal(value: string | null | undefined): string {
  if (!value) return "";
  return value.slice(0, 16);
}

import { TEMPERATURE_HOT_THRESHOLD, TEMPERATURE_WARM_THRESHOLD } from "@/lib/constants";

/** Clase Tailwind de color para la "temperatura" de un chollo. */
export function temperatureColor(temperature: number): string {
  if (temperature >= TEMPERATURE_HOT_THRESHOLD) return "text-alert-red";
  if (temperature >= TEMPERATURE_WARM_THRESHOLD) return "text-cyan-glow";
  return "text-muted-foreground";
}
