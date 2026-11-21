/**
 * Textos del sitio que leen buscadores y asistentes de IA: descripción de la
 * marca y preguntas frecuentes. Se muestran tal cual en la página (portada y
 * «Sobre nosotros»), en el JSON-LD `FAQPage` y en `/llms.txt`, así que todo lo
 * que dicen tiene que ser cierto y comprobable en el producto.
 */
import type { FaqItem } from "./schema";

export const SITE_TAGLINE = "Chollos y ofertas de tecnología en España, verificados a diario";

export const SITE_SUMMARY =
  "BuenChollo Tech es una web española de chollos y ofertas de tecnología y electrónica: móviles, portátiles, audio, televisores, gaming, informática y domótica. Cada oferta se revisa antes de publicarse y una comprobación automática diaria vigila el precio y el stock en la tienda; cuando el descuento desaparece, el chollo se marca como terminado.";

export const SITE_FAQ: FaqItem[] = [
  {
    question: "¿Qué es BuenChollo Tech?",
    answer:
      "Una web española que reúne chollos y ofertas de tecnología y electrónica (móviles, portátiles, audio, televisores, gaming, informática y domótica) en tiendas como Amazon. También publica las mejores ofertas en su canal de Telegram.",
  },
  {
    question: "¿Cómo sé que un chollo sigue disponible?",
    answer:
      "Cada chollo se revisa antes de publicarse y, en los de Amazon, una comprobación automática diaria consulta el precio y el stock. Si el precio sube o el producto se agota, la oferta se marca como terminada y deja de anunciarse como chollo.",
  },
  {
    question: "¿Es gratis usar BuenChollo Tech?",
    answer:
      "Sí. Consultar los chollos y crear una cuenta es gratis. Con cuenta puedes guardar favoritos, votar y crear alertas de precio.",
  },
  {
    question: "¿Cómo puedo recibir avisos de nuevos chollos?",
    answer:
      "Crea una alerta por palabra clave, marca, categoría, tienda, precio máximo o descuento mínimo: te avisamos en la web y con un resumen por correo. También puedes seguir el canal de Telegram de BuenChollo Tech.",
  },
  {
    question: "¿Cómo gana dinero BuenChollo Tech?",
    answer:
      "Algunos enlaces son de afiliado: si compras a través de ellos, la tienda nos paga una pequeña comisión sin que el precio cambie para ti.",
  },
  {
    question: "¿Puedo compartir un chollo que haya encontrado?",
    answer:
      "Sí. Con una cuenta puedes proponer un chollo desde «Publicar chollo»; el equipo lo revisa antes de publicarlo.",
  },
  {
    question: "¿Qué son «Los chollos de la semana»?",
    answer:
      "Cada domingo publicamos en nuestros canales de Telegram y WhatsApp un resumen con los chollos activos con más descuento de los últimos 7 días (hasta 10). En la portada, el «Top de la semana» muestra ese mismo ranking en directo.",
  },
  {
    question: "¿Cómo veo los chollos nuevos desde mi última visita?",
    answer:
      "Sin necesidad de cuenta: junto a «Inicio» te indicamos cuántos chollos se han publicado desde tu última visita, y en la portada una línea marca dónde empiezan los que ya viste.",
  },
  {
    question: "¿Qué significa el porcentaje de descuento?",
    answer:
      "Es la rebaja del precio actual respecto al precio anterior o de referencia que indica la tienda. Lo mostramos junto al precio anterior para que puedas comparar.",
  },
  {
    question: "¿Puede cambiar el precio de un chollo?",
    answer:
      "Sí. Las tiendas cambian sus precios en cualquier momento y el precio válido es siempre el que ves en la tienda al comprar. Los precios de Amazon los comprobamos a diario y, si una oferta termina, la ficha lo indica.",
  },
  {
    question: "¿Dónde se compra el producto?",
    answer:
      "Siempre en la tienda que ofrece el chollo, por ejemplo Amazon. BuenChollo Tech no vende productos ni gestiona pedidos, envíos, garantías ni devoluciones: de todo eso se encarga la tienda.",
  },
  {
    question: "¿Tenéis canal de WhatsApp?",
    answer:
      "Sí. Además del canal de Telegram, puedes seguir nuestro Canal de WhatsApp. Encontrarás los enlaces a los dos en la barra de navegación y en el menú de la web.",
  },
];
