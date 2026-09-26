import type { ComponentType } from "react";
import {
  ArrowRight,
  Eye,
  FileText,
  Globe2,
  MousePointerClick,
  Search,
  Send,
  Users,
} from "lucide-react";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";

import type { AnalyticsOverview, AnalyticsSourceRow } from "@/services/api/analytics";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const chartConfig = {
  views: { label: "Visitas", color: "var(--color-chart-1)" },
  visitors: { label: "Visitantes", color: "var(--color-chart-2)" },
} satisfies ChartConfig;

const SOURCE_META = {
  telegram: { label: "Telegram", icon: Send },
  organic: { label: "Búsqueda orgánica", icon: Search },
  referral: { label: "Otras webs", icon: Globe2 },
  direct: { label: "Directo / desconocido", icon: MousePointerClick },
} as const;

function formatNumber(value: number): string {
  return Math.max(0, Math.trunc(value))
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

function MetricCard({
  label,
  value,
  description,
  icon: Icon,
}: {
  label: string;
  value: number;
  description: string;
  icon: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="font-mono text-xs uppercase text-muted-foreground">
            {label}
          </CardTitle>
          <Icon className="size-4 text-primary" aria-hidden />
        </div>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <p className="font-mono text-3xl font-bold tabular-nums">{formatNumber(value)}</p>
      </CardContent>
    </Card>
  );
}

function SourceLabel({ row }: { row: AnalyticsSourceRow }) {
  const meta = SOURCE_META[row.source];
  const Icon = meta.icon;
  return (
    <div className="flex items-center gap-2">
      <Icon className="size-4 text-primary" aria-hidden />
      <span>{meta.label}</span>
    </div>
  );
}

export function AnalyticsDashboard({ data }: { data: AnalyticsOverview }) {
  const totals = data.totals;

  return (
    <div className="flex flex-col gap-6">
      <section
        aria-labelledby="traffic-summary"
        className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
      >
        <h2 id="traffic-summary" className="sr-only">
          Resumen de tráfico
        </h2>
        <MetricCard
          label="Visitas"
          value={totals.page_views}
          description="Cargas públicas registradas"
          icon={Eye}
        />
        <MetricCard
          label="Visitantes únicos"
          value={totals.unique_visitors}
          description="Navegadores distintos"
          icon={Users}
        />
        <MetricCard
          label="Sesiones"
          value={totals.sessions}
          description="Bloques de navegación"
          icon={MousePointerClick}
        />
        <MetricCard
          label="Visitas al blog"
          value={totals.blog_views}
          description="Lecturas de artículos"
          icon={FileText}
        />
      </section>

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex flex-col gap-1">
              <CardTitle>Telegram → blog</CardTitle>
              <CardDescription>
                Visitantes cuya sesión comenzó en el enlace del canal y terminó leyendo el blog.
              </CardDescription>
            </div>
            <Badge variant="outline">ATRIBUCIÓN FIRST-TOUCH</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid items-center gap-3 sm:grid-cols-[1fr_auto_1fr_auto_1fr]">
            <div className="rounded-lg bg-muted p-4">
              <p className="font-mono text-xs uppercase text-muted-foreground">
                Llegan de Telegram
              </p>
              <p className="mt-2 font-mono text-3xl font-bold tabular-nums">
                {formatNumber(totals.telegram_visitors)}
              </p>
            </div>
            <ArrowRight className="mx-auto size-5 text-muted-foreground" aria-hidden />
            <div className="rounded-lg bg-muted p-4">
              <p className="font-mono text-xs uppercase text-muted-foreground">Entran al blog</p>
              <p className="mt-2 font-mono text-3xl font-bold tabular-nums">
                {formatNumber(totals.telegram_blog_visitors)}
              </p>
            </div>
            <ArrowRight className="mx-auto size-5 text-muted-foreground" aria-hidden />
            <div className="rounded-lg bg-primary p-4 text-primary-foreground">
              <p className="font-mono text-xs uppercase opacity-70">Conversión</p>
              <p className="mt-2 font-mono text-4xl font-bold tabular-nums">
                {totals.telegram_to_blog_rate}%
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Evolución de audiencia</CardTitle>
          <CardDescription>Visitas y visitantes únicos por día.</CardDescription>
        </CardHeader>
        <CardContent>
          {data.timeseries.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">
              Aún no hay tráfico en este periodo.
            </p>
          ) : (
            <ChartContainer config={chartConfig} className="min-h-[260px] w-full">
              <AreaChart data={data.timeseries} accessibilityLayer margin={{ left: 4, right: 4 }}>
                <CartesianGrid vertical={false} />
                <XAxis
                  dataKey="date"
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  tickFormatter={(value: string) => value.slice(5)}
                />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={32} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Area
                  dataKey="views"
                  type="monotone"
                  fill="var(--color-views)"
                  fillOpacity={0.2}
                  stroke="var(--color-views)"
                  strokeWidth={2}
                />
                <Area
                  dataKey="visitors"
                  type="monotone"
                  fill="var(--color-visitors)"
                  fillOpacity={0.08}
                  stroke="var(--color-visitors)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ChartContainer>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Procedencia</CardTitle>
          <CardDescription>El origen se conserva durante toda la sesión.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Origen</TableHead>
                <TableHead className="text-right">Visitantes</TableHead>
                <TableHead className="text-right">Sesiones</TableHead>
                <TableHead className="text-right">Visitas</TableHead>
                <TableHead className="text-right">Blog</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.sources.map((row) => (
                <TableRow key={row.source}>
                  <TableCell className="font-medium">
                    <SourceLabel row={row} />
                  </TableCell>
                  <TableCell className="text-right font-mono tabular-nums">
                    {formatNumber(row.visitors)}
                  </TableCell>
                  <TableCell className="text-right font-mono tabular-nums">
                    {formatNumber(row.sessions)}
                  </TableCell>
                  <TableCell className="text-right font-mono tabular-nums">
                    {formatNumber(row.views)}
                  </TableCell>
                  <TableCell className="text-right font-mono tabular-nums">
                    {formatNumber(row.blog_views)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Páginas más vistas</CardTitle>
            <CardDescription>Rutas públicas con mayor consumo.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ruta</TableHead>
                  <TableHead className="text-right">Visitas</TableHead>
                  <TableHead className="text-right">Únicos</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.top_pages.map((row) => (
                  <TableRow key={row.path}>
                    <TableCell className="max-w-56 truncate font-mono text-xs">
                      {row.path}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {formatNumber(row.views)}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {formatNumber(row.visitors)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Artículos con más alcance</CardTitle>
            <CardDescription>Lecturas del periodo y contador público acumulado.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Artículo</TableHead>
                  <TableHead className="text-right">Únicos</TableHead>
                  <TableHead className="text-right">Público</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.top_articles.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell>
                      <a className="font-medium hover:text-primary" href={`/blog/${row.slug}`}>
                        {row.title}
                      </a>
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {formatNumber(row.visitors)}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {formatNumber(row.view_count)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
