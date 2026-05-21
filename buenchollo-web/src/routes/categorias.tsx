import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { categoriesService, type Category } from "@/services/api/categories";
import { Layout } from "@/components/Layout";

const SITE = "https://buenchollotech.lovable.app";

export const Route = createFileRoute("/categorias")({
  component: CategoriesPage,
  head: () => ({
    meta: [
      { title: "Todas las categorías de chollos · BuencholloTech" },
      { name: "description", content: "Explora todas las categorías y subcategorías de chollos: móviles, portátiles, audio, TV, gaming, smart home y más." },
      { property: "og:title", content: "Todas las categorías de chollos" },
      { property: "og:description", content: "Categorías y subcategorías para encontrar tu chollo de tecnología." },
      { property: "og:url", content: `${SITE}/categorias` },
    ],
    links: [{ rel: "canonical", href: `${SITE}/categorias` }],
  }),
});

function CategoriesPage() {
  const [cats, setCats] = useState<Category[]>([]);
  useEffect(() => {
    categoriesService.getAll().then(setCats).catch(console.error);
  }, []);
  const top = cats.filter(c => !c.parent_id);
  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
        <div className="font-mono text-cyan-glow text-xs mb-2">&gt; CATEGORIAS</div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tighter mb-8">Todas las categorías</h1>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {top.map(t => {
            const subs = cats.filter(c => c.parent_id === t.id);
            return (
              <div key={t.id} className="bg-surface-800 border border-surface-700 p-5 hover:border-cyan-glow transition-colors">
                <Link to="/categoria/$slug" params={{ slug: t.slug }} className="font-bold text-lg block mb-3 hover:text-cyan-glow">{t.name}</Link>
                <ul className="space-y-1.5">
                  {subs.map(s => (
                    <li key={s.id}>
                      <Link to="/categoria/$slug" params={{ slug: s.slug }} className="text-sm text-muted-foreground hover:text-foreground font-mono">› {s.name}</Link>
                    </li>
                  ))}
                  {subs.length === 0 && <li className="text-xs text-muted-foreground font-mono">Sin subcategorías</li>}
                </ul>
              </div>
            );
          })}
        </div>
      </div>
    </Layout>
  );
}
