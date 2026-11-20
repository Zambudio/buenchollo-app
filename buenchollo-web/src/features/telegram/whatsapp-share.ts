/**
 * Compartir a mano el post en el Canal de WhatsApp (no hay API oficial para
 * publicar en Canales). En el móvil se abre la hoja de compartir del sistema
 * con la imagen y el texto; si no se puede, se abre WhatsApp solo con el texto.
 */

async function imageFile(imageUrl: string): Promise<File | null> {
  try {
    const response = await fetch(imageUrl);
    if (!response.ok) return null;
    const blob = await response.blob();
    const extension = blob.type.split("/")[1] || "jpg";
    return new File([blob], `chollo.${extension}`, { type: blob.type || "image/jpeg" });
  } catch {
    // CORS de la CDN o red: se comparte solo el texto
    return null;
  }
}

export async function copyWhatsAppText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

/** Devuelve false si el usuario canceló la hoja de compartir. */
export async function shareToWhatsApp(text: string, imageUrl: string | null): Promise<boolean> {
  if (typeof navigator.share === "function") {
    const data: ShareData = { text };
    const file = imageUrl ? await imageFile(imageUrl) : null;
    if (file && navigator.canShare?.({ files: [file] })) data.files = [file];
    try {
      await navigator.share(data);
      return true;
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return false;
      // Navegador sin soporte real: se cae a WhatsApp con el texto
    }
  }
  window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank", "noopener,noreferrer");
  return true;
}
