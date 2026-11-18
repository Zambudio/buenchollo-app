import { createFileRoute, Link } from "@tanstack/react-router";
import { Layout } from "@/components/layout/Layout";
import { SiteFaq } from "@/features/home/SiteFaq";
import { absoluteUrl, pageHead, withBrand } from "@/lib/seo/head";
import { breadcrumbSchema, ORGANIZATION_ID, organizationSchema } from "@/lib/seo/schema";
import { SITE_SUMMARY } from "@/lib/seo/site-content";
import { CONTACT_EMAIL, TELEGRAM_URL } from "@/lib/site";

const DESCRIPTION =
  "Quiénes somos y cómo trabajamos: cómo seleccionamos y verificamos cada chollo de tecnología, cómo se financia BuenChollo Tech y cómo contactar.";

export const Route = createFileRoute("/sobre-nosotros")({
  component: SobreNosotros,
  head: () =>
    pageHead({
      title: withBrand("Sobre nosotros: cómo seleccionamos los chollos"),
      description: DESCRIPTION,
      path: "/sobre-nosotros",
      jsonLd: [
        {
          "@type": "AboutPage",
          name: "Sobre BuenChollo Tech",
          url: absoluteUrl("/sobre-nosotros"),
          description: DESCRIPTION,
          inLanguage: "es-ES",
          about: { "@id": ORGANIZATION_ID },
        },
        organizationSchema(),
        breadcrumbSchema([
          { name: "Inicio", path: "/" },
          { name: "Sobre nosotros", path: "/sobre-nosotros" },
        ]),
      ],
    }),
});

const STEPS = [
  {
    title: "Seleccionamos",
    text: "Cada chollo se publica a mano o llega como propuesta de la comunidad, y el equipo lo revisa antes de publicarlo: precio, tienda, descuento real y que el producto merezca la pena.",
  },
  {
    title: "Verificamos a diario",
    text: "Una comprobación automática consulta cada día el precio y el stock en la tienda. Si el precio sube o el producto se agota, la oferta se marca como terminada para que no compres un chollo que ya no lo es.",
  },
  {
    title: "La comunidad opina",
    text: "Los usuarios votan y comentan cada chollo: la temperatura refleja si la oferta convence de verdad.",
  },
  {
    title: "Te avisamos",
    text: "Las alertas gratuitas te avisan en la web y por correo cuando aparece un chollo que encaja con lo que buscas, y el canal de Telegram difunde los mejores.",
  },
];

function SobreNosotros() {
  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
        <nav
          aria-label="Ruta de navegación"
          className="font-mono text-xs text-muted-foreground mb-8"
        >
          <Link to="/" className="hover:text-cyan-glow">
            INICIO
          </Link>{" "}
          / SOBRE NOSOTROS
        </nav>

        <h1 className="text-3xl sm:text-4xl font-bold tracking-tighter mb-4">
          Sobre BuenChollo Tech
        </h1>
        <p className="text-muted-foreground leading-relaxed mb-10">{SITE_SUMMARY}</p>

        <h2 className="text-xl font-bold tracking-tight mb-4">Cómo seleccionamos los chollos</h2>
        <ol className="grid gap-3 sm:grid-cols-2 mb-10">
          {STEPS.map((step, index) => (
            <li
              key={step.title}
              className="bg-surface-800 border border-surface-700 rounded-lg p-4"
            >
              <div className="font-mono text-xs text-cyan-glow mb-1">0{index + 1}</div>
              <h3 className="font-semibold mb-1">{step.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{step.text}</p>
            </li>
          ))}
        </ol>

        <h2 className="text-xl font-bold tracking-tight mb-3">Transparencia</h2>
        <p className="text-muted-foreground leading-relaxed mb-10">
          Algunos enlaces son de afiliado: si compras a través de ellos, la tienda nos paga una
          pequeña comisión y el precio no cambia para ti. Es lo que permite mantener la web
          gratuita.
        </p>

        <h2 className="text-xl font-bold tracking-tight mb-3">Contacto</h2>
        <p className="text-muted-foreground leading-relaxed">
          Escríbenos a{" "}
          <a href={`mailto:${CONTACT_EMAIL}`} className="text-cyan-glow hover:underline">
            {CONTACT_EMAIL}
          </a>{" "}
          o síguenos en nuestro{" "}
          <a href={TELEGRAM_URL} className="text-cyan-glow hover:underline" rel="noopener">
            canal de Telegram
          </a>
          . Si ves un chollo que ya no está disponible, escríbenos o coméntalo en su ficha.
        </p>

        <SiteFaq />
      </div>
    </Layout>
  );
}
