/** Lectura de imágenes desde portapapeles y arrastrar-soltar para "Publicar chollo". */

export interface ClipboardImages {
  files: File[];
  urls: string[];
}

const EMPTY = (): ClipboardImages => ({ files: [], urls: [] });

function toHttpUrl(raw: string): string | null {
  const value = raw.trim();
  if (!value || /\s/.test(value)) return null;
  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed.href : null;
  } catch {
    return null;
  }
}

function transferOf(source: ClipboardEvent | DataTransfer): DataTransfer | null {
  if (typeof (source as DataTransfer).getData === "function") return source as DataTransfer;
  return (source as ClipboardEvent).clipboardData ?? null;
}

function imageFiles(dt: DataTransfer): File[] {
  const files = Array.from(dt.files ?? []).filter((f) => f.type.startsWith("image/"));
  if (files.length) return files;
  return Array.from(dt.items ?? [])
    .filter((item) => item.kind === "file" && item.type.startsWith("image/"))
    .map((item) => item.getAsFile())
    .filter((f): f is File => f !== null);
}

function htmlImageUrls(html: string): string[] {
  if (!html || typeof DOMParser === "undefined") return [];
  const doc = new DOMParser().parseFromString(html, "text/html");
  return Array.from(doc.querySelectorAll("img"))
    .map((img) => toHttpUrl(img.getAttribute("src") ?? ""))
    .filter((u): u is string => u !== null);
}

const unique = (values: string[]) => Array.from(new Set(values));

/** Imágenes de un `paste` o de un `drop`: primero ficheros `image/*`; si no hay,
 *  `src` http(s) de los `<img>` del HTML, luego `text/uri-list` y por último
 *  `text/plain` si es una URL http(s). El texto normal no devuelve nada. */
export function extractClipboardItems(source: ClipboardEvent | DataTransfer): ClipboardImages {
  const dt = transferOf(source);
  if (!dt) return EMPTY();

  const files = imageFiles(dt);
  if (files.length) return { files, urls: [] };

  const fromHtml = htmlImageUrls(dt.getData("text/html"));
  if (fromHtml.length) return { files: [], urls: unique(fromHtml) };

  const fromUriList = dt
    .getData("text/uri-list")
    .split(/\r?\n/)
    .filter((line) => !line.startsWith("#"))
    .map(toHttpUrl)
    .filter((u): u is string => u !== null);
  if (fromUriList.length) return { files: [], urls: unique(fromUriList) };

  const fromText = toHttpUrl(dt.getData("text/plain"));
  return fromText ? { files: [], urls: [fromText] } : EMPTY();
}

export function hasPlainText(e: ClipboardEvent): boolean {
  return Boolean(e.clipboardData?.getData("text/plain").trim());
}

const NON_TEXT_INPUTS = new Set([
  "button",
  "checkbox",
  "color",
  "file",
  "hidden",
  "image",
  "radio",
  "range",
  "reset",
  "submit",
]);

/** ¿El elemento acepta texto pegado? (input de texto, textarea o contenteditable). */
export function isTextEntryElement(el: Element | null): boolean {
  if (!el) return false;
  if (el instanceof HTMLTextAreaElement) return true;
  if (el instanceof HTMLInputElement) return !NON_TEXT_INPUTS.has(el.type);
  return el instanceof HTMLElement && el.isContentEditable === true;
}

const extensionFor = (mime: string) => mime.split("/")[1]?.split("+")[0] || "png";

/** Lee imágenes y URL con la Clipboard API asíncrona (botón "Pegar").
 *  Lanza si el navegador deniega el permiso. */
export async function readClipboardImages(clipboard: Clipboard): Promise<ClipboardImages> {
  const out = EMPTY();
  const items = await clipboard.read();
  for (const [index, item] of items.entries()) {
    const imageType = item.types.find((t) => t.startsWith("image/"));
    if (imageType) {
      const blob = await item.getType(imageType);
      out.files.push(
        new File([blob], `portapapeles-${index + 1}.${extensionFor(imageType)}`, {
          type: imageType,
        }),
      );
      continue;
    }
    if (item.types.includes("text/plain")) {
      const text = await (await item.getType("text/plain")).text();
      const url = toHttpUrl(text);
      if (url) out.urls.push(url);
    }
  }
  return out;
}

export function canReadClipboard(): boolean {
  return typeof navigator !== "undefined" && typeof navigator.clipboard?.read === "function";
}
