import { useRouterState } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { touchVisit, visitBaseline } from "@/lib/lastVisit";
import { dealsService } from "@/services/api/deals";

// Una petición por carga de página aunque la barra se vuelva a montar al navegar.
let countRequest: Promise<number> | null = null;

function newDealsCount(): Promise<number> {
  const baseline = visitBaseline();
  if (!baseline) return Promise.resolve(0);
  countRequest ??= dealsService.countNewSince(baseline).catch(() => 0);
  return countRequest;
}

/**
 * «N nuevos» junto a «Inicio» en la barra de navegación: chollos publicados
 * desde la última visita. Va dentro del primer enlace para que se vea también
 * en el móvil (la barra se desplaza en horizontal). Solo en el navegador, si
 * hubo una visita anterior y hay alguno nuevo; un fallo de la API no la muestra.
 * También mantiene viva la visita al navegar y al volver a la pestaña.
 */
export function NewDealsBadge() {
  const [count, setCount] = useState(0);
  const pathname = useRouterState({ select: (state) => state.location.pathname });

  useEffect(() => {
    let cancelled = false;
    void newDealsCount().then((n) => {
      if (!cancelled) setCount(n);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    touchVisit();
  }, [pathname]);

  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === "visible") touchVisit();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, []);

  if (count <= 0) return null;
  return (
    <span className="new-deals-badge" title="Chollos publicados desde tu última visita">
      <span className="new-deals-badge-dot" aria-hidden="true" />
      {count > 99 ? "99+" : count}
      <span className="sr-only">{count === 1 ? " nuevo" : " nuevos"} desde tu última visita</span>
      <span aria-hidden="true">{count === 1 ? " nuevo" : " nuevos"}</span>
    </span>
  );
}
