import { createFileRoute, Link } from "@tanstack/react-router";
import { Layout } from "@/components/layout/Layout";
import { SITE_URL, SITE_NAME, CONTACT_EMAIL } from "@/lib/site";

const TITLE = `Política de cookies | ${SITE_NAME}`;
const DESCRIPTION =
  "BuenChollo Tech no usa cookies de analítica ni de publicidad. Solo almacenamos técnicamente la sesión de inicio de sesión en tu navegador.";

export const Route = createFileRoute("/politica-de-cookies")({
  component: PoliticaDeCookies,
  head: () => ({
    meta: [
      { title: TITLE },
      { name: "description", content: DESCRIPTION },
      { name: "robots", content: "index, follow" },
      { property: "og:title", content: TITLE },
      { property: "og:description", content: DESCRIPTION },
      { property: "og:type", content: "website" },
      { property: "og:url", content: `${SITE_URL}/politica-de-cookies` },
    ],
    links: [{ rel: "canonical", href: `${SITE_URL}/politica-de-cookies` }],
  }),
});

function PoliticaDeCookies() {
  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-16">
        <nav className="font-mono text-xs text-muted-foreground mb-8">
          <Link to="/" className="hover:text-cyan-glow">
            INICIO
          </Link>{" "}
          / POLÍTICA DE COOKIES
        </nav>

        <h1 className="font-mono text-2xl font-bold uppercase tracking-tight mb-2">
          Política de cookies
        </h1>
        <div className="h-px bg-cyan-glow/40 mb-4" />
        <p className="font-mono text-xs text-muted-foreground mb-8">
          Última actualización: 6 de julio de 2026
        </p>

        <div
          className="prose prose-invert max-w-none
            prose-headings:font-mono prose-headings:uppercase prose-headings:tracking-tight
            prose-headings:text-foreground prose-h2:text-lg prose-h2:mt-10
            prose-a:text-cyan-glow prose-a:no-underline hover:prose-a:underline
            prose-strong:text-foreground prose-li:marker:text-cyan-glow"
        >
          <p>
            Esta política explica, de forma honesta y sin categorías innecesarias, qué almacenamos
            en tu navegador cuando usas {SITE_NAME} y por qué. Si tienes cualquier duda, escríbenos
            a <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.
          </p>

          <h2>1. Qué es una cookie o el almacenamiento local</h2>
          <p>
            Una cookie (o el almacenamiento local del navegador, «localStorage») es un pequeño
            fragmento de información que una web guarda en tu dispositivo para recordar datos entre
            visitas o entre páginas: por ejemplo, para mantenerte identificado tras iniciar sesión.
          </p>

          <h2>2. Qué NO usamos</h2>
          <p>
            {SITE_NAME} <strong>no utiliza</strong> cookies ni tecnologías equivalentes de:
          </p>
          <ul>
            <li>Analítica o medición de audiencia (por ejemplo, Google Analytics).</li>
            <li>Publicidad o publicidad personalizada.</li>
            <li>Seguimiento (tracking) entre webs o creación de perfiles publicitarios.</li>
            <li>Redes sociales incrustadas con seguimiento propio.</li>
          </ul>
          <p>
            No existen, por tanto, categorías de cookies «analíticas» o «de marketing» que aceptar o
            rechazar: no las hay.
          </p>

          <h2>3. Lo único que almacenamos: tu sesión</h2>
          <p>
            El único dato que guardamos en tu navegador es el <strong>token de sesión</strong> que
            genera nuestro proveedor de autenticación (Supabase) cuando inicias sesión. Se guarda en
            el <strong>almacenamiento local (localStorage)</strong> de tu navegador, no en una
            cookie tradicional, y sirve exclusivamente para reconocerte como usuario autenticado en
            visitas y páginas sucesivas sin pedirte la contraseña cada vez.
          </p>
          <p>
            Este almacenamiento es <strong>estrictamente necesario</strong> para el funcionamiento
            del inicio de sesión: sin él no podríamos mantenerte identificado ni ofrecerte funciones
            como favoritos, alertas o comentarios asociados a tu cuenta. Por tratarse de una
            funcionalidad esencial, no requiere tu consentimiento previo conforme a la normativa
            aplicable, aunque igualmente te informamos de ello en esta página y mediante un aviso la
            primera vez que visitas la web.
          </p>

          <h2>4. Cómo «desactivarlo»</h2>
          <p>
            Al no haber cookies opcionales, no existe un panel de preferencias con interruptores que
            activar o desactivar. Si prefieres que tu navegador no conserve esta información, puedes
            borrar los datos de navegación (cookies y datos de sitios) correspondientes al dominio
            buenchollotech.com desde la configuración de tu navegador. Ten en cuenta que esto
            cerrará tu sesión y tendrás que volver a iniciarla la próxima vez que quieras usar las
            funciones de tu cuenta.
          </p>

          <h2>5. Aviso al visitar la web</h2>
          <p>
            La primera vez que visitas {SITE_NAME} te mostramos un aviso breve informándote de este
            uso exclusivamente técnico del almacenamiento local. Al pulsar «Entendido», simplemente
            confirmas que has leído el aviso; no se activa ningún tratamiento adicional ni cambia el
            funcionamiento de la web.
          </p>

          <h2>6. Cambios futuros</h2>
          <p>
            Si en algún momento incorporásemos herramientas no esenciales (por ejemplo, de
            analítica), actualizaríamos esta política, dejaríamos de considerarlas necesarias por
            defecto y solicitaríamos tu consentimiento real y específico antes de activarlas.
          </p>

          <hr />
          <p>
            Consulta también nuestra{" "}
            <Link to="/politica-de-privacidad">Política de privacidad</Link> y nuestros{" "}
            <Link to="/terminos-y-condiciones">Términos y condiciones</Link>.
          </p>
        </div>

        <div className="mt-10">
          <Link
            to="/"
            className="inline-flex items-center justify-center border border-cyan-glow/50 text-cyan-glow font-mono text-xs px-5 py-3 hover:bg-cyan-glow/10 transition-colors"
          >
            ← Volver al inicio
          </Link>
        </div>
      </div>
    </Layout>
  );
}
