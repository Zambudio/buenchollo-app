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
      "Cada chollo se revisa antes de publicarse y una comprobación automática diaria consulta el precio y el stock en la tienda. Si el precio sube o el producto se agota, la oferta se marca como terminada y deja de anunciarse como chollo.",
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
];
