import { createFileRoute, Link } from "@tanstack/react-router";
import { Layout } from "@/components/layout/Layout";
import { SITE_URL, SITE_NAME, CONTACT_EMAIL } from "@/lib/site";

const TITLE = `Términos y condiciones | ${SITE_NAME}`;
const DESCRIPTION =
  "Condiciones de uso de BuenChollo Tech: naturaleza informativa del servicio, enlaces de afiliado, cuenta de usuario, propiedad intelectual, responsabilidad y legislación aplicable.";

export const Route = createFileRoute("/terminos-y-condiciones")({
  component: TerminosYCondiciones,
  head: () => ({
    meta: [
      { title: TITLE },
      { name: "description", content: DESCRIPTION },
      { name: "robots", content: "index, follow" },
      { property: "og:title", content: TITLE },
      { property: "og:description", content: DESCRIPTION },
      { property: "og:type", content: "website" },
      { property: "og:url", content: `${SITE_URL}/terminos-y-condiciones` },
    ],
    links: [{ rel: "canonical", href: `${SITE_URL}/terminos-y-condiciones` }],
  }),
});

function TerminosYCondiciones() {
  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-16">
        <nav className="font-mono text-xs text-muted-foreground mb-8">
          <Link to="/" className="hover:text-cyan-glow">
            INICIO
          </Link>{" "}
          / TÉRMINOS Y CONDICIONES
        </nav>

        <h1 className="font-mono text-2xl font-bold uppercase tracking-tight mb-2">
          Términos y condiciones
        </h1>
        <div className="h-px bg-cyan-glow/40 mb-4" />
        <p className="font-mono text-xs text-muted-foreground mb-8">
          Última actualización: 4 de julio de 2026
        </p>

        <div
          className="prose prose-invert max-w-none
            prose-headings:font-mono prose-headings:uppercase prose-headings:tracking-tight
            prose-headings:text-foreground prose-h2:text-lg prose-h2:mt-10
            prose-a:text-cyan-glow prose-a:no-underline hover:prose-a:underline
            prose-strong:text-foreground prose-li:marker:text-cyan-glow"
        >
          <p>
            Estas condiciones regulan el uso de la web {SITE_NAME}. Al utilizar el servicio, aceptas
            estas condiciones. Si no estás de acuerdo con ellas, no utilices la web.
          </p>

          <h2>1. Identificación del servicio</h2>
          <ul>
            <li>
              <strong>Servicio:</strong> {SITE_NAME}.
            </li>
            <li>
              <strong>Responsable:</strong> Pedro Javier Zambudio Decillis.
            </li>
            <li>
              <strong>Contacto:</strong> <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.
            </li>
            <li>
              <strong>Dominio:</strong> buenchollotech.com.
            </li>
          </ul>

          <h2>2. Objeto del servicio</h2>
          <p>
            {SITE_NAME} recopila, organiza y publica ofertas, descuentos e información sobre
            productos tecnológicos, con el objetivo de ayudarte a descubrir chollos reales de
            tecnología y electrónica.
          </p>

          <h2>3. Naturaleza informativa</h2>
          <p>El servicio tiene carácter informativo. En particular:</p>
          <ul>
            <li>{SITE_NAME} no es el vendedor de los productos.</li>
            <li>
              Las compras se formalizan en las plataformas o comercios externos correspondientes.
            </li>
            <li>
              El precio final, la disponibilidad, el envío, la garantía y las condiciones de venta
              dependen del comercio correspondiente.
            </li>
            <li>Los precios y las existencias pueden cambiar sin previo aviso.</li>
            <li>
              Debes verificar siempre el precio final y las condiciones en la web del comercio antes
              de comprar.
            </li>
          </ul>

          <h2>4. Enlaces de afiliado</h2>
          <p>
            Algunos de los enlaces publicados en {SITE_NAME} pueden ser enlaces de afiliado,
            incluido el programa de afiliados de <strong>Amazon</strong>. Esto significa que, si
            accedes a una tienda a través de uno de esos enlaces y completas una compra, {SITE_NAME}{" "}
            puede recibir una comisión. Esta comisión{" "}
            <strong>no supone ningún coste adicional</strong> para ti ni afecta al precio que pagas.
          </p>

          <h2>5. Registro y cuenta</h2>
          <ul>
            <li>
              Puedes crear una cuenta mediante correo electrónico y contraseña o iniciando sesión
              con Google.
            </li>
            <li>
              Eres responsable de mantener la confidencialidad de tus credenciales y de la actividad
              realizada desde tu cuenta.
            </li>
            <li>Te comprometes a facilitar información veraz y legítima.</li>
            <li>
              Puedes cerrar sesión o solicitar la eliminación de tu cuenta en cualquier momento.
            </li>
            <li>
              Podremos suspender o cancelar cuentas en caso de uso abusivo, fraudulento o de
              incumplimiento de estas condiciones.
            </li>
          </ul>

          <h2>6. Uso permitido</h2>
          <p>Al utilizar {SITE_NAME}, te comprometes a no:</p>
          <ul>
            <li>Realizar un uso fraudulento del servicio.</li>
            <li>Acceder sin autorización a áreas o datos restringidos.</li>
            <li>
              Utilizar automatizaciones abusivas o interferir con el funcionamiento del servicio.
            </li>
            <li>Extraer masivamente datos o contenidos.</li>
            <li>Suplantar a otras personas o entidades.</li>
            <li>
              Publicar contenido ilícito, ofensivo o que infrinja derechos de terceros en las
              funciones que permiten comentarios.
            </li>
          </ul>

          <h2>7. Propiedad intelectual</h2>
          <ul>
            <li>
              La marca, el diseño y los contenidos propios de {SITE_NAME} pertenecen a su
              responsable.
            </li>
            <li>
              Las marcas, imágenes, nombres de producto y fichas técnicas pertenecen a sus
              respectivos fabricantes, comercios o titulares y se muestran únicamente con fines
              informativos.
            </li>
            <li>
              {SITE_NAME} no reclama derechos sobre las marcas ni las imágenes propiedad de
              terceros.
            </li>
          </ul>

          <h2>8. Servicios y enlaces externos</h2>
          <p>
            {SITE_NAME} contiene enlaces a webs y servicios de terceros. Estas páginas externas se
            rigen por sus propias condiciones y políticas de privacidad, y {SITE_NAME} no controla
            ni se responsabiliza de su funcionamiento ni de su contenido.
          </p>

          <h2>9. Disponibilidad del servicio</h2>
          <p>
            El servicio se ofrece «tal cual» y puede sufrir interrupciones, cambios, tareas de
            mantenimiento o la retirada de funcionalidades. No garantizamos su disponibilidad
            permanente ni ininterrumpida.
          </p>

          <h2>10. Responsabilidad</h2>
          <p>En la medida permitida por la ley, {SITE_NAME} no se hace responsable de:</p>
          <ul>
            <li>Errores de precio o de información.</li>
            <li>Ofertas caducadas o ya no disponibles.</li>
            <li>Falta de stock.</li>
            <li>Cambios en las condiciones aplicados por el vendedor.</li>
            <li>Información proporcionada por terceros.</li>
            <li>Problemas ocurridos en plataformas o comercios externos.</li>
          </ul>
          <p>
            Nada de lo anterior excluye ni limita las responsabilidades que legalmente no puedan
            excluirse, ni los derechos imperativos que te correspondan como consumidor.
          </p>

          <h2>11. Privacidad</h2>
          <p>
            El tratamiento de tus datos personales se describe en nuestra{" "}
            <Link to="/politica-de-privacidad">Política de privacidad</Link>.
          </p>

          <h2>12. Modificaciones</h2>
          <p>
            Podemos actualizar estas condiciones. Cuando los cambios sean relevantes, lo
            reflejaremos en esta página actualizando la fecha de «Última actualización» que figura
            al inicio.
          </p>

          <h2>13. Legislación aplicable</h2>
          <p>
            Estas condiciones se rigen por la legislación española, sin perjuicio de los derechos
            imperativos que correspondan a los consumidores según su lugar de residencia habitual.
          </p>

          <hr />
          <p>
            Consulta también nuestra{" "}
            <Link to="/politica-de-privacidad">Política de privacidad</Link>.
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
