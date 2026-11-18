import { SITE_FAQ } from "@/lib/seo/site-content";

/** Preguntas frecuentes visibles. Son las mismas del JSON-LD `FAQPage`: los
 *  buscadores y asistentes de IA solo deben citar lo que el usuario ve. */
export function SiteFaq({ headingLevel = "h2" }: { headingLevel?: "h2" | "h3" }) {
  const Heading = headingLevel;
  return (
    <section aria-labelledby="site-faq-heading" className="mt-12 border-t border-surface-700 pt-8">
      <Heading id="site-faq-heading" className="text-xl font-bold tracking-tight mb-4">
        Preguntas frecuentes
      </Heading>
      <div className="space-y-2">
        {SITE_FAQ.map((item) => (
          <details
            key={item.question}
            className="group bg-surface-800 border border-surface-700 rounded-lg px-4 py-3"
          >
            <summary className="cursor-pointer font-medium text-foreground marker:text-cyan-glow">
              {item.question}
            </summary>
            <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{item.answer}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
