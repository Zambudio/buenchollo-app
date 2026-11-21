import { createFileRoute, Link } from "@tanstack/react-router";
import { Layout } from "@/components/layout/Layout";
import { SiteFaq } from "@/features/home/SiteFaq";
import { pageHead } from "@/lib/seo/head";
import { faqPageSeo } from "@/lib/seo/faq";

export const Route = createFileRoute("/preguntas-frecuentes")({
  component: PreguntasFrecuentes,
  head: () => pageHead(faqPageSeo()),
});

function PreguntasFrecuentes() {
  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-3">Preguntas frecuentes</h1>
        <p className="text-muted-foreground leading-relaxed">
          Cómo funciona BuenChollo Tech, cómo verificamos los chollos y cómo enterarte de los
          mejores. ¿No encuentras tu respuesta?{" "}
          <Link to="/contacto" className="text-cyan-glow hover:underline">
            Escríbenos
          </Link>
          .
        </p>
        <SiteFaq showHeading={false} />
      </div>
    </Layout>
  );
}
