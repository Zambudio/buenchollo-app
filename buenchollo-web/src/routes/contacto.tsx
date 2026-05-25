import { createFileRoute, Link } from "@tanstack/react-router";
import { Layout } from "@/components/Layout";
import { Mail } from "lucide-react";

export const Route = createFileRoute("/contacto")({
  component: Contacto,
});

function Contacto() {
  return (
    <Layout>
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-16">
        <nav className="font-mono text-xs text-muted-foreground mb-8">
          <Link to="/" className="hover:text-cyan-glow">INICIO</Link> / CONTACTO
        </nav>

        <h1 className="font-mono text-2xl font-bold uppercase tracking-tight mb-2">
          Contacto
        </h1>
        <div className="h-px bg-cyan-glow/40 mb-8" />

        <div className="bg-surface-800 border border-surface-700 p-8">
          <p className="text-muted-foreground leading-relaxed mb-6">
            Si tienes preguntas, sugerencias o quieres reportar algún problema, no dudes en ponerte en contacto con nosotros.
          </p>
          <a
            href="mailto:buenchollotech@gmail.com"
            className="inline-flex items-center gap-3 border border-cyan-glow/50 text-cyan-glow font-mono text-sm px-5 py-3 hover:bg-cyan-glow/10 transition-colors"
          >
            <Mail className="size-4" />
            buenchollotech@gmail.com
          </a>
        </div>
      </div>
    </Layout>
  );
}
