import { createFileRoute, Link } from "@tanstack/react-router";
import { Layout } from "@/components/layout/Layout";
import { SITE_URL, SITE_NAME, CONTACT_EMAIL } from "@/lib/site";

const TITLE = `Política de privacidad | ${SITE_NAME}`;
const DESCRIPTION =
  "Cómo trata BuenChollo Tech tus datos personales: inicio de sesión con Google, datos de cuenta, finalidades, proveedores, conservación, derechos y eliminación de datos.";

export const Route = createFileRoute("/politica-de-privacidad")({
  component: PoliticaDePrivacidad,
  head: () => ({
    meta: [
      { title: TITLE },
      { name: "description", content: DESCRIPTION },
      { name: "robots", content: "index, follow" },
      { property: "og:title", content: TITLE },
      { property: "og:description", content: DESCRIPTION },
      { property: "og:type", content: "website" },
      { property: "og:url", content: `${SITE_URL}/politica-de-privacidad` },
    ],
    links: [{ rel: "canonical", href: `${SITE_URL}/politica-de-privacidad` }],
  }),
});

function PoliticaDePrivacidad() {
  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-16">
        <nav className="font-mono text-xs text-muted-foreground mb-8">
          <Link to="/" className="hover:text-cyan-glow">
            INICIO
          </Link>{" "}
          / POLÍTICA DE PRIVACIDAD
        </nav>

        <h1 className="font-mono text-2xl font-bold uppercase tracking-tight mb-2">
          Política de privacidad
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
            En {SITE_NAME} nos tomamos en serio tu privacidad. Esta política explica qué datos
            personales tratamos, con qué finalidad, sobre qué base jurídica, con quién los
            compartimos técnicamente y qué derechos tienes. Está redactada para ser comprensible; si
            tienes cualquier duda, escríbenos a{" "}
            <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.
          </p>

          <h2>1. Responsable del tratamiento</h2>
          <ul>
            <li>
              <strong>Responsable:</strong> Pedro Javier Zambudio Decillis.
            </li>
            <li>
              <strong>Proyecto:</strong> {SITE_NAME}.
            </li>
            <li>
              <strong>Dominio:</strong> buenchollotech.com.
            </li>
            <li>
              <strong>Contacto de privacidad:</strong>{" "}
              <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.
            </li>
          </ul>

          <h2>2. Ámbito de aplicación</h2>
          <p>
            Esta política se aplica al uso de la web {SITE_NAME}, al registro de usuarios, al inicio
            de sesión (incluido el acceso mediante Google) y a las funcionalidades asociadas a tu
            cuenta, como alertas, favoritos, votos y comentarios.
          </p>

          <h2>3. Datos que tratamos</h2>
          <p>Tratamos únicamente los datos necesarios para prestar el servicio:</p>
          <ul>
            <li>
              <strong>Datos de identidad y cuenta:</strong> dirección de correo electrónico e
              identificador único de usuario, gestionados a través de nuestro proveedor de
              autenticación (Supabase). Si accedes con Google, se incluyen también los datos básicos
              de perfil que Google facilita (ver apartado 4).
            </li>
            <li>
              <strong>Datos de perfil (opcionales):</strong> nombre para mostrar, nombre de usuario,
              biografía e imagen de avatar, si decides completarlos.
            </li>
            <li>
              <strong>Datos de uso de la cuenta:</strong> chollos marcados como favoritos, alertas
              que configures y tus preferencias de notificación, votos en chollos, comentarios que
              publiques y notificaciones internas.
            </li>
            <li>
              <strong>Datos técnicos:</strong> información técnica derivada del acceso a la web
              (como la dirección IP y datos de tráfico), tratada por nuestro proveedor de
              infraestructura (Cloudflare) con fines de seguridad y funcionamiento, así como
              información mínima de errores para diagnóstico técnico, configurada para no incluir
              datos personales adicionales de forma predeterminada.
            </li>
          </ul>
          <p>
            No tratamos categorías especiales de datos y no te pedimos más información de la
            necesaria para las funciones que utilices.
          </p>

          <h2>4. Inicio de sesión con Google</h2>
          <p>
            Puedes acceder a {SITE_NAME} con tu cuenta de Google. En ese caso, a través de nuestro
            proveedor de autenticación (Supabase), recibimos de Google la información asociada a los
            permisos estándar de identidad (<strong>openid</strong>, <strong>email</strong> y{" "}
            <strong>profile</strong>):
          </p>
          <ul>
            <li>El identificador de tu cuenta de Google (mediante OpenID).</li>
            <li>Tu dirección de correo electrónico.</li>
            <li>
              Datos básicos de perfil (como el nombre y la imagen de perfil) que Google incluye.
            </li>
          </ul>
          <p>
            <strong>Para qué usamos estos datos:</strong> únicamente para identificarte, crear o
            vincular tu cuenta, mantener tu sesión iniciada, prestarte las funcionalidades asociadas
            a tu perfil y prevenir fraudes, abusos o accesos no autorizados.
          </p>
          <p>
            <strong>Dónde se almacenan y durante cuánto tiempo:</strong> se almacenan en nuestra
            infraestructura sobre Supabase y se conservan mientras tu cuenta esté activa o hasta que
            solicites su eliminación (ver apartados 9 y 10).
          </p>
          <p>Declaramos de forma expresa que:</p>
          <ul>
            <li>
              <strong>No</strong> accedemos a tu Gmail, Google Drive, contactos, calendario ni a
              ningún otro servicio de tu cuenta de Google. Solo utilizamos los datos de
              autenticación indicados.
            </li>
            <li>
              <strong>No</strong> vendemos los datos obtenidos de Google.
            </li>
            <li>
              <strong>No</strong> los utilizamos para publicidad personalizada.
            </li>
            <li>
              <strong>No</strong> los cedemos a terceros para sus propios fines comerciales.
            </li>
            <li>
              Solo se utilizan para autenticación, gestión de tu cuenta y prestación de las
              funcionalidades que solicitas.
            </li>
          </ul>
          <p>
            Puedes solicitar la eliminación de estos datos en cualquier momento tal como se describe
            en el apartado 10.
          </p>

          <h2>5. Finalidades del tratamiento</h2>
          <ul>
            <li>
              <strong>Registro y autenticación:</strong> crear tu cuenta y permitirte iniciar
              sesión.
            </li>
            <li>
              <strong>Gestión de la cuenta y prestación de funcionalidades:</strong> favoritos,
              alertas, votos, comentarios y notificaciones.
            </li>
            <li>
              <strong>Comunicaciones de servicio:</strong> notificaciones de las alertas que hayas
              configurado, según tus preferencias.
            </li>
            <li>
              <strong>Atención de consultas:</strong> responder a las comunicaciones que nos envíes.
            </li>
            <li>
              <strong>Seguridad y prevención de abuso:</strong> proteger el servicio y a los
              usuarios.
            </li>
            <li>
              <strong>Cumplimiento de obligaciones legales</strong> cuando resulte aplicable.
            </li>
          </ul>

          <h2>6. Bases jurídicas</h2>
          <ul>
            <li>
              <strong>Ejecución de la relación con el usuario:</strong> crear y gestionar tu cuenta
              y prestarte las funcionalidades solicitadas.
            </li>
            <li>
              <strong>Interés legítimo:</strong> seguridad, prevención de fraude, protección del
              servicio y notificaciones internas de funcionamiento.
            </li>
            <li>
              <strong>Consentimiento:</strong> notificaciones opcionales por correo electrónico de
              tus alertas, que puedes activar o desactivar cuando quieras.
            </li>
            <li>
              <strong>Cumplimiento de obligaciones legales</strong> cuando corresponda.
            </li>
          </ul>
          <p>
            Aceptar esta política no equivale a un consentimiento general para todos los
            tratamientos: cada finalidad se apoya en la base jurídica que le corresponde.
          </p>

          <h2>7. Destinatarios y proveedores</h2>
          <p>
            No vendemos tus datos ni los cedemos a terceros para sus fines propios. Para prestar el
            servicio nos apoyamos en proveedores tecnológicos que actúan como encargados o
            responsables según el caso:
          </p>
          <ul>
            <li>
              <strong>Supabase:</strong> autenticación, base de datos e infraestructura de
              almacenamiento.
            </li>
            <li>
              <strong>Google:</strong> proveedor de identidad cuando eliges iniciar sesión con
              Google.
            </li>
            <li>
              <strong>Cloudflare:</strong> entrega de contenidos, seguridad e infraestructura de
              red.
            </li>
            <li>
              <strong>Proveedor de correo electrónico:</strong> gestión de las comunicaciones
              enviadas a nuestras direcciones de contacto.
            </li>
          </ul>
          <p>
            Otros servicios que utilizamos internamente <strong>no</strong> tratan datos personales
            de los usuarios: la publicación de chollos en canales públicos (Telegram) y la
            generación de textos de las ofertas se realizan sin incluir información personal de las
            cuentas.
          </p>

          <h2>8. Transferencias internacionales</h2>
          <p>
            Algunos de nuestros proveedores tecnológicos pueden tratar información desde países
            situados fuera del Espacio Económico Europeo. En esos casos se aplicarán los mecanismos
            y garantías legales previstos por la normativa de protección de datos para dichas
            transferencias.
          </p>

          <h2>9. Conservación</h2>
          <p>Conservamos tus datos:</p>
          <ul>
            <li>Mientras tu cuenta esté activa.</li>
            <li>Mientras sea necesario para prestarte el servicio.</li>
            <li>Durante los plazos necesarios para atender posibles responsabilidades legales.</li>
            <li>Hasta que solicites su eliminación, cuando proceda.</li>
          </ul>
          <p>
            No aplicamos actualmente un borrado automático por plazos fijos; los datos se eliminan a
            solicitud del usuario o cuando dejan de ser necesarios para las finalidades descritas.
          </p>

          <h2>10. Eliminación de cuenta y datos</h2>
          <p>
            Actualmente la eliminación de la cuenta no está disponible como opción de autoservicio
            en la web. Puedes solicitar la eliminación o anonimización de tus datos escribiendo a{" "}
            <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>. Atenderemos tu solicitud y
            eliminaremos o anonimizaremos los datos asociados a tu cuenta, salvo aquellos que
            debamos conservar por obligación legal o para atender responsabilidades.
          </p>

          <h2>11. Tus derechos</h2>
          <p>Puedes ejercer los siguientes derechos:</p>
          <ul>
            <li>Acceso a tus datos.</li>
            <li>Rectificación de datos inexactos.</li>
            <li>Supresión.</li>
            <li>Oposición al tratamiento.</li>
            <li>Limitación del tratamiento.</li>
            <li>Portabilidad.</li>
            <li>Retirada del consentimiento cuando el tratamiento dependa de él.</li>
          </ul>
          <p>
            Para ejercerlos, escríbenos a <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.
            Si consideras que no hemos atendido correctamente tus derechos, puedes presentar una
            reclamación ante la Agencia Española de Protección de Datos (
            <a href="https://www.aepd.es" target="_blank" rel="noopener noreferrer">
              www.aepd.es
            </a>
            ).
          </p>

          <h2>12. Seguridad</h2>
          <p>
            Aplicamos medidas técnicas y organizativas razonables para proteger tus datos, como el
            uso de conexiones cifradas (HTTPS/TLS), autenticación basada en tokens y control de
            acceso. Ningún sistema es infalible, por lo que no podemos garantizar una seguridad
            absoluta.
          </p>

          <h2>13. Cookies y almacenamiento local</h2>
          <p>
            {SITE_NAME} utiliza exclusivamente almacenamiento técnico necesario para el
            funcionamiento del inicio de sesión y el mantenimiento de tu sesión: tu sesión se guarda
            en el almacenamiento local de tu navegador mediante nuestro proveedor de autenticación.
            No utilizamos cookies ni herramientas de analítica, publicidad o seguimiento no
            esenciales. La primera vez que visitas la web te mostramos un aviso informativo breve
            sobre este almacenamiento técnico —sin categorías de cookies que aceptar o rechazar,
            porque no existen—, que puedes cerrar pulsando «Entendido». Puedes consultar el detalle
            completo en nuestra <Link to="/politica-de-cookies">Política de cookies</Link>. Si en el
            futuro incorporásemos herramientas no esenciales, actualizaríamos esta política y
            gestionaríamos el consentimiento correspondiente.
          </p>

          <h2>14. Menores</h2>
          <p>
            El servicio no está dirigido específicamente a menores de edad. Si detectamos que se ha
            creado una cuenta sin la capacidad legal necesaria, procederemos a su eliminación.
          </p>

          <h2>15. Decisiones automatizadas</h2>
          <p>
            No adoptamos decisiones automatizadas ni elaboramos perfiles con efectos jurídicos o
            significativos sobre los usuarios.
          </p>

          <h2>16. Cambios en esta política</h2>
          <p>
            Podemos actualizar esta política para reflejar cambios en el servicio o en la normativa
            aplicable. Cuando los cambios sean relevantes, lo indicaremos en esta misma página
            actualizando la fecha de «Última actualización» que figura al inicio.
          </p>

          <hr />
          <p>
            Consulta también nuestros{" "}
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
