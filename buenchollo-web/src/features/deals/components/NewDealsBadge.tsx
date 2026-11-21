import { Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { visitBaseline } from "@/lib/lastVisit";
import { dealsService } from "@/services/api/deals";

/**
 * Píldora «N nuevos» en la barra de navegación: chollos publicados desde la
 * última visita. Solo aparece en el navegador, si hubo una visita anterior y
 * hay alguno nuevo; un fallo de la API simplemente no la muestra.
 */
export function NewDealsBadge() {
  const [count, setCount] = useState(0);
  useEffect(() => {
    const baseline = visitBaseline();
    if (!baseline) return;
    let cancelled = false;
    dealsService
      .countNewSince(baseline)
      .then((n) => {
        if (!cancelled) setCount(n);
      })
      .catch(() => {
        /* no crítico */
      });
    return () => {
      cancelled = true;
    };
  }, []);
  if (count <= 0) return null;
  const label = count === 1 ? "1 nuevo" : `${count > 99 ? "99+" : count} nuevos`;
  return (
    <Link
      to="/"
      hash="home-deals-heading"
      className="new-deals-badge"
      title="Chollos publicados desde tu última visita"
    >
      <span className="new-deals-badge-dot" aria-hidden="true" />
      {label}
      <span className="sr-only"> desde tu última visita</span>
    </Link>
  );
}
