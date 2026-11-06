import { createFileRoute, Link } from "@tanstack/react-router";
import {
  ArrowRight,
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
import { categoriesService } from "@/services/api/categories";
import { dealsService } from "@/services/api/deals";
import { Layout } from "@/components/layout/Layout";
import { withFallback } from "@/lib/fallback";

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
  loader: async () => {
    const [cats, deals] = await Promise.all([
      withFallback(categoriesService.getAll(), [], "Error cargando el listado de categorías"),
      withFallback(dealsService.getLatest(50), [], "Error cargando portadas de categorías"),
    ]);
    const covers: Record<string, string> = {};
    for (const deal of deals) {
      if (deal.category?.slug && deal.image_url && !covers[deal.category.slug]) {
        covers[deal.category.slug] = deal.image_url;
      }
    }
    return { cats, covers };
  },
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
  const { cats, covers } = Route.useLoaderData();
  const top = cats.filter((c) => !c.parent_id);
  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
        <span className="eyebrow">Explora a tu manera</span>
        <h1 className="category-page-title">Encuentra tu próximo favorito</h1>
        <p className="category-page-lead">
          Entra en una categoría para ver sus chollos y votar los productos que merecen estar
          arriba.
        </p>
        <nav aria-label="Categorías principales" className="category-visual-strip">
          {top.map((category) => {
            const Icon = CATEGORY_ICONS[category.slug] ?? Package;
            return (
              <Link
                key={category.id}
                to="/categoria/$slug"
                params={{ slug: category.slug }}
                className="category-visual-item"
              >
                <span className="category-visual-image">
                  <Icon size={42} strokeWidth={1.4} aria-hidden="true" />
                  {covers[category.slug] && (
                    <img
                      src={covers[category.slug]}
                      alt=""
                      loading="lazy"
                      width="104"
                      height="104"
                      onError={(event) => {
                        event.currentTarget.style.display = "none";
                      }}
                    />
                  )}
                </span>
                <span>{category.name}</span>
              </Link>
            );
          })}
        </nav>
        <div className="category-directory-heading">
          <h2>Todas las categorías</h2>
          <span>Elige una subcategoría y descubre su top</span>
        </div>
        <div className="category-directory">
          {top.map((t) => {
            const subs = cats.filter((c) => c.parent_id === t.id);
            const Icon = CATEGORY_ICONS[t.slug] ?? Package;
            return (
              <section key={t.id} className="category-directory-card">
                <h3>
                  <Icon size={22} strokeWidth={1.8} aria-hidden="true" />
                  <Link to="/categoria/$slug" params={{ slug: t.slug }}>
                    {t.name} <ArrowRight size={16} aria-hidden="true" />
                  </Link>
                </h3>
                <ul>
                  {subs.map((s) => (
                    <li key={s.id}>
                      <Link to="/categoria/$slug" params={{ slug: s.slug }}>
                        {s.name}
                      </Link>
                    </li>
                  ))}
                  {subs.length === 0 && (
                    <li className="text-xs text-muted-foreground">Sin subcategorías</li>
                  )}
                </ul>
              </section>
            );
          })}
        </div>
      </div>
    </Layout>
  );
}
