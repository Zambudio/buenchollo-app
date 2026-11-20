import { useEffect, useState } from "react";
import { countdownTo, formatCountdown } from "@/lib/campaigns";

/**
 * Cuenta atrás que se actualiza cada 30 s. En el servidor (y en el primer
 * render del cliente) muestra `fallback` para no provocar un desajuste de
 * hidratación con la hora del servidor.
 */
export function CampaignCountdown({
  target,
  fallback,
  className,
}: {
  target: Date;
  fallback: string;
  className?: string;
}) {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    setNow(new Date());
    const timer = window.setInterval(() => setNow(new Date()), 30_000);
    return () => window.clearInterval(timer);
  }, []);
  return (
    <span className={className} aria-live="off">
      {now ? formatCountdown(countdownTo(target, now)) : fallback}
    </span>
  );
}
