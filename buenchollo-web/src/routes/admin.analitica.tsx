import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { ShieldCheck, ShieldOff } from "lucide-react";
import { toast } from "sonner";

import { AnalyticsDashboard } from "@/features/analytics/components/AnalyticsDashboard";
import { useAnalyticsOverview } from "@/features/analytics/hooks/useAnalyticsOverview";
import { isAnalyticsExcluded, setAnalyticsExcluded } from "@/features/analytics/lib/tracking";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { errorMessage } from "@/lib/errors";

export const Route = createFileRoute("/admin/analitica")({ component: AdminAnalyticsPage });

function AdminAnalyticsPage() {
  const [days, setDays] = useState(30);
  const [excluded, setExcluded] = useState(false);
  const { data, error, isLoading } = useAnalyticsOverview(days);

  useEffect(() => {
    setExcluded(isAnalyticsExcluded(window.localStorage));
  }, []);

  useEffect(() => {
    if (error) toast.error(errorMessage(error, "No se pudo cargar la analítica"));
  }, [error]);

  const toggleExclusion = () => {
    const next = !excluded;
    setAnalyticsExcluded(window.localStorage, next);
    setExcluded(next);
    toast.success(next ? "Este dispositivo queda excluido" : "Este dispositivo vuelve a medirse");
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase text-primary">AUDIENCIA / ATRIBUCIÓN</p>
          <h2 className="mt-1 text-2xl font-bold tracking-tight">¿De dónde llegan y qué leen?</h2>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Visitas reales del navegador. Telegram conserva su origen aunque la persona entre
            primero en la portada y llegue al blog después.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Select value={String(days)} onValueChange={(value) => setDays(Number(value))}>
            <SelectTrigger className="w-36" aria-label="Periodo de analítica">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectItem value="7">Últimos 7 días</SelectItem>
                <SelectItem value="30">Últimos 30 días</SelectItem>
                <SelectItem value="90">Últimos 90 días</SelectItem>
              </SelectGroup>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={toggleExclusion}>
            {excluded ? (
              <ShieldOff data-icon="inline-start" />
            ) : (
              <ShieldCheck data-icon="inline-start" />
            )}
            {excluded ? "Dispositivo excluido" : "Excluir este dispositivo"}
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Cargando analítica">
          {Array.from({ length: 4 }, (_, index) => (
            <Skeleton key={index} className="h-32" />
          ))}
        </div>
      ) : data ? (
        <AnalyticsDashboard data={data} />
      ) : (
        <p className="rounded-lg border border-border p-6 text-sm text-muted-foreground">
          No hay datos disponibles para este periodo.
        </p>
      )}
    </div>
  );
}
