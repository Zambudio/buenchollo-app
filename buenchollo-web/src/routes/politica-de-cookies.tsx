import { createFileRoute, Link } from "@tanstack/react-router";
import { Layout } from "@/components/layout/Layout";
import { AnalyticsPreferenceButton } from "@/features/analytics/components/AnalyticsPreferenceButton";
import { SITE_URL, SITE_NAME, CONTACT_EMAIL } from "@/lib/site";

const TITLE = `Política de cookies | ${SITE_NAME}`;
const DESCRIPTION =
  "Cómo usa BuenChollo Tech el almacenamiento local para la sesión y una medición propia, anónima y limitada de audiencia.";

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
          Última actualización: 26 de septiembre de 2026
        </p>

        <div
          className="prose dark:prose-invert max-w-none
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

          <h2>2. Qué no usamos</h2>
          <p>
            {SITE_NAME} <strong>no utiliza</strong> herramientas de:
          </p>
          <ul>
            <li>Publicidad o publicidad personalizada.</li>
            <li>Seguimiento (tracking) entre webs o creación de perfiles publicitarios.</li>
            <li>Redes sociales incrustadas con seguimiento propio.</li>
            <li>Cesión de datos de navegación a una plataforma de analítica externa.</li>
          </ul>
          <p>
            La medición descrita a continuación es propia, se limita a estadísticas agregadas de
            audiencia y no se combina con datos de tu cuenta ni se reutiliza para otros fines.
          </p>

          <h2>3. Almacenamiento necesario para tu sesión</h2>
          <p>
            Cuando inicias sesión guardamos el <strong>token de sesión</strong> que genera nuestro
            proveedor de autenticación (Supabase). Se guarda en el{" "}
            <strong>almacenamiento local (localStorage)</strong> de tu navegador, no en una cookie
            tradicional, y sirve exclusivamente para reconocerte como usuario autenticado en visitas
            y páginas sucesivas sin pedirte la contraseña cada vez.
          </p>
          <p>
            Este almacenamiento es <strong>estrictamente necesario</strong> para el funcionamiento
            del inicio de sesión: sin él no podríamos mantenerte identificado ni ofrecerte funciones
            como favoritos, alertas o comentarios asociados a tu cuenta. Por tratarse de una
            funcionalidad esencial, no requiere tu consentimiento previo conforme a la normativa
            aplicable, aunque igualmente te informamos de ello en esta página y mediante un aviso la
            primera vez que visitas la web.
          </p>

          <h2>4. Medición propia y anónima de audiencia</h2>
          <p>
            Para saber si las páginas y los artículos se leen, utilizamos una solución alojada en
            nuestra propia infraestructura. El navegador genera un identificador aleatorio, sin
            nombre, correo ni datos de tu cuenta. La API lo transforma inmediatamente mediante HMAC
            antes de almacenarlo y <strong>no guarda tu dirección IP</strong> en esta analítica.
          </p>
          <p>Registramos únicamente:</p>
          <ul>
            <li>La ruta visitada y la fecha.</li>
            <li>El origen general de la sesión: Telegram, buscador, otra web o acceso directo.</li>
            <li>El dominio de referencia y etiquetas UTM, cuando existen.</li>
            <li>Un identificador seudónimo de visitante y otro de sesión.</li>
          </ul>
          <p>
            El identificador de visitante se conserva como máximo <strong>395 días</strong>. La
            sesión termina tras <strong>30 minutos de inactividad</strong>. Los eventos del servidor
            se conservan un máximo de <strong>25 meses</strong> y después se eliminan. No usamos
            esta información para publicidad, seguimiento entre sitios ni decisiones individuales.
          </p>

          <h2>5. Cómo excluir este dispositivo</h2>
          <p>
            Puedes desactivar esta medición en este navegador sin perder acceso a la web. La
            preferencia se guarda localmente y no afecta a tu sesión de usuario. También puedes
            borrar todos los datos de buenchollotech.com desde la configuración del navegador; esto
            cerrará cualquier sesión iniciada.
          </p>
          <AnalyticsPreferenceButton />

          <h2>6. Aviso al visitar la web</h2>
          <p>
            La primera vez que visitas {SITE_NAME} mostramos un aviso informativo. Al pulsar
            «Entendido» confirmas que lo has leído; no se habilita publicidad ni seguimiento de
            terceros.
          </p>

          <h2>7. Cambios futuros</h2>
          <p>
            Si incorporamos herramientas de terceros, publicidad, perfiles o cualquier uso que
            requiera consentimiento, actualizaremos esta política y solicitaremos una elección real
            antes de activarlo.
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
