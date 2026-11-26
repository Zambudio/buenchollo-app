/** Qué pasó con la versión WhatsApp al publicar (respuesta de `/telegram/notify`). */
export function whatsappNotice(result: {
  whatsapp_sent?: boolean;
  whatsapp_queued?: boolean;
}): string {
  if (result.whatsapp_queued) return "Saldrá en el Canal de WhatsApp en unos minutos";
  if (result.whatsapp_sent) return "La versión WhatsApp está en el canal Admin, lista para copiar";
  return "La versión WhatsApp no llegó al canal Admin (¿canal sin configurar?)";
}
