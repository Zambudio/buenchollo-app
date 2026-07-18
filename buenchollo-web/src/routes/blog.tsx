import { createFileRoute } from "@tanstack/react-router";
import { Layout } from "@/components/layout/Layout";

const SITE = "https://buenchollotech.com";

export const Route = createFileRoute("/blog")({
  component: BlogPage,
  head: () => ({
    meta: [
      { title: "Blog · BuenChollo Tech" },
      {
        name: "description",
        content:
          "Artículos, guías de compra y análisis sobre tecnología y chollos. Próximamente en BuenChollo Tech.",
      },
      { property: "og:title", content: "Blog · BuenChollo Tech" },
      {
        property: "og:description",
        content: "Artículos, guías de compra y análisis sobre tecnología y chollos.",
      },
      { property: "og:url", content: `${SITE}/blog` },
      { property: "og:type", content: "website" },
    ],
    links: [{ rel: "canonical", href: `${SITE}/blog` }],
  }),
});

function BlogPage() {
  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-24 text-center">
        <div className="font-mono text-cyan-glow text-xs tracking-[0.2em] mb-3">&gt; BLOG</div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tighter mb-4">Próximamente</h1>
        <p className="text-muted-foreground text-base leading-relaxed">
          Estamos preparando artículos, guías de compra y análisis de chollos de tecnología. Vuelve
          pronto.
        </p>
      </div>
    </Layout>
  );
}
