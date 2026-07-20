import { logError } from "@/lib/logger";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  BatteryCharging,
  Camera,
  Cpu,
  Gamepad2,
  HardDrive,
  Headphones,
  House,
  Laptop,
  Mouse,
  Package,
  Smartphone,
  Tv,
  Watch,
  Wifi,
  type LucideIcon,
} from "lucide-react";
import { categoriesService, type Category } from "@/services/api/categories";
import { Layout } from "@/components/layout/Layout";

const SITE = "https://buenchollotech.com";

const CATEGORY_ICONS: Record<string, LucideIcon> = {
  informatica: Laptop,
  "componentes-pc": Cpu,
  almacenamiento: HardDrive,
  perifericos: Mouse,
  audio: Headphones,
  "gaming-y-consolas": Gamepad2,
  "smartphones-y-tablets": Smartphone,
  "tv-e-imagen": Tv,
  "fotografia-y-video": Camera,
  redes: Wifi,
  domotica: House,
  wearables: Watch,
  energia: BatteryCharging,
  "varios-xly2": Package,
};

export const Route = createFileRoute("/categorias")({
  component: CategoriesPage,
  head: () => ({
    meta: [
      { title: "Todas las categorías de chollos · BuenChollo Tech" },
      {
        name: "description",
        content:
          "Explora todas las categorías y subcategorías de chollos: móviles, portátiles, audio, TV, gaming, smart home y más.",
      },
      { property: "og:title", content: "Todas las categorías de chollos" },
      {
        property: "og:description",
        content: "Categorías y subcategorías para encontrar tu chollo de tecnología.",
      },
      { property: "og:url", content: `${SITE}/categorias` },
    ],
    links: [{ rel: "canonical", href: `${SITE}/categorias` }],
  }),
});

function CategoriesPage() {
  const [cats, setCats] = useState<Category[]>([]);
  useEffect(() => {
    categoriesService
      .getAll()
      .then(setCats)
      .catch((error) => logError("Error cargando el listado de categorías", error));
  }, []);
  const top = cats.filter((c) => !c.parent_id);
  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
        <div className="font-mono text-cyan-glow text-xs mb-2">&gt; CATEGORIAS</div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tighter mb-8">
          Todas las categorías
        </h1>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {top.map((t) => {
            const subs = cats.filter((c) => c.parent_id === t.id);
            const Icon = CATEGORY_ICONS[t.slug] ?? Package;
            return (
              <div
                key={t.id}
                className="group relative overflow-hidden bg-surface-800 border border-surface-700 p-5 hover:border-cyan-glow transition-colors"
              >
                <div
                  aria-hidden="true"
                  className="pointer-events-none absolute right-4 top-4 flex size-14 items-center justify-center rounded-xl border border-cyan-glow/25 bg-gradient-to-br from-cyan-glow/20 to-blue-500/5 text-cyan-glow shadow-[0_0_20px_rgba(0,229,255,0.12)] transition-all duration-300 group-hover:scale-105 group-hover:border-cyan-glow/60 group-hover:shadow-[0_0_26px_rgba(0,229,255,0.28)]"
                >
                  <Icon
                    className="size-8 drop-shadow-[0_0_8px_rgba(0,229,255,0.45)]"
                    strokeWidth={1.8}
                  />
                </div>
                <Link
                  to="/categoria/$slug"
                  params={{ slug: t.slug }}
                  className="relative block min-h-12 pr-14 mb-3 font-bold text-lg hover:text-cyan-glow"
                >
                  {t.name}
                </Link>
                <ul className="space-y-1.5">
                  {subs.map((s) => (
                    <li key={s.id}>
                      <Link
                        to="/categoria/$slug"
                        params={{ slug: s.slug }}
                        className="text-sm text-muted-foreground hover:text-foreground font-mono"
                      >
                        › {s.name}
                      </Link>
                    </li>
                  ))}
                  {subs.length === 0 && (
                    <li className="text-xs text-muted-foreground font-mono">Sin subcategorías</li>
                  )}
                </ul>
              </div>
            );
          })}
        </div>
      </div>
    </Layout>
  );
}
