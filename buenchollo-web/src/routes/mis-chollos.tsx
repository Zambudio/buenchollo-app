import { createFileRoute } from "@tanstack/react-router";
import { Layout } from "@/components/layout/Layout";

export const Route = createFileRoute("/mis-chollos")({
  component: MySubmissionsPage,
  head: () => ({
    meta: [
      { title: "Mis chollos · BuenChollo Tech" },
      { name: "robots", content: "noindex, nofollow" },
    ],
  }),
});

function MySubmissionsPage() {
  return (
    <Layout>
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
        <h1 className="text-3xl font-bold tracking-tighter mb-4">Mis chollos</h1>
        <p className="text-muted-foreground font-mono">Próximamente</p>
      </div>
    </Layout>
  );
}
