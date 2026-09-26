import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { isAnalyticsExcluded, setAnalyticsExcluded } from "@/features/analytics/lib/tracking";

export function AnalyticsPreferenceButton() {
  const [excluded, setExcluded] = useState(false);

  useEffect(() => {
    setExcluded(isAnalyticsExcluded(window.localStorage));
  }, []);

  const toggle = () => {
    const next = !excluded;
    setAnalyticsExcluded(window.localStorage, next);
    setExcluded(next);
  };

  return (
    <div className="not-prose mt-5 rounded-lg border border-cyan-glow/25 bg-surface-800/70 p-4">
      <p className="mb-3 font-mono text-xs text-muted-foreground">
        {excluded
          ? "La medición está desactivada en este dispositivo."
          : "Este dispositivo participa en la medición anónima de audiencia."}
      </p>
      <Button type="button" variant="outline" size="sm" onClick={toggle}>
        {excluded ? "Volver a activar la medición" : "Excluir este dispositivo"}
      </Button>
    </div>
  );
}
