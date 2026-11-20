import { useEffect, useState } from "react";
import { countdownTo, formatCountdown, type Countdown } from "@/lib/campaigns";

const UNITS: { key: keyof Countdown; label: string }[] = [
  { key: "days", label: "días" },
  { key: "hours", label: "horas" },
  { key: "minutes", label: "min" },
  { key: "seconds", label: "seg" },
];

const pad = (n: number) => String(n).padStart(2, "0");

/**
 * Cuenta atrás en «tubos de neón» que avanza cada segundo. En el servidor (y
 * en el primer render del cliente) pinta guiones con la misma caja, para no
 * mover el diseño ni provocar un desajuste de hidratación; `fallback` es el
 * texto accesible hasta que hay hora del cliente.
 */
export function CampaignCountdown({ target, fallback }: { target: Date; fallback: string }) {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    setNow(new Date());
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  const left = now ? countdownTo(target, now) : null;
  return (
    <div
      className="neon-countdown"
      role="timer"
      aria-label={left ? formatCountdown(left) : fallback}
    >
      {UNITS.map(({ key, label }, i) => (
        <div key={key} className="neon-countdown-cell" aria-hidden="true">
          <span className={`neon-countdown-tube${i === UNITS.length - 1 ? " is-seconds" : ""}`}>
            {left ? pad(left[key]) : "--"}
          </span>
          <span className="neon-countdown-label">{label}</span>
        </div>
      ))}
    </div>
  );
}
