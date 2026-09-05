import { supabase } from "@/integrations/supabase/client";

export interface CropArea {
  x: number;
  y: number;
  width: number;
  height: number;
}

const OUTPUT_MAX_SIDE = 2560;
const OUTPUT_TYPE = "image/jpeg";
const OUTPUT_QUALITY = 0.92;

function loadImage(sourceUrl: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.crossOrigin = "anonymous";
    image.onload = () => resolve(image);
    image.onerror = () =>
      reject(
        new Error(
          "No se pudo preparar esta imagen para recortarla. El servidor de origen no permite editarla.",
        ),
      );
    image.src = sourceUrl;
  });
}

function canvasToBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    try {
      canvas.toBlob(
        (blob) => {
          if (blob) resolve(blob);
          else reject(new Error("No se pudo generar la imagen recortada."));
        },
        OUTPUT_TYPE,
        OUTPUT_QUALITY,
      );
    } catch {
      reject(
        new Error(
          "El origen de la imagen bloquea el recorte. Prueba con otra imagen o súbela al chollo primero.",
        ),
      );
    }
  });
}

export async function createCroppedImage(sourceUrl: string, crop: CropArea): Promise<Blob> {
  const image = await loadImage(sourceUrl);
  const sourceX = Math.round(crop.x * image.naturalWidth);
  const sourceY = Math.round(crop.y * image.naturalHeight);
  const sourceWidth = Math.max(1, Math.round(crop.width * image.naturalWidth));
  const sourceHeight = Math.max(1, Math.round(crop.height * image.naturalHeight));
  const scale = Math.min(1, OUTPUT_MAX_SIDE / Math.max(sourceWidth, sourceHeight));

  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(sourceWidth * scale));
  canvas.height = Math.max(1, Math.round(sourceHeight * scale));

  const context = canvas.getContext("2d");
  if (!context) throw new Error("El navegador no permite procesar esta imagen.");

  // Telegram presenta las fotos sobre fondos variables; evitamos transparencias negras al exportar JPEG.
  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = "high";
  context.drawImage(
    image,
    sourceX,
    sourceY,
    sourceWidth,
    sourceHeight,
    0,
    0,
    canvas.width,
    canvas.height,
  );

  return canvasToBlob(canvas);
}

export async function cropAndUploadTelegramImage(
  sourceUrl: string,
  crop: CropArea,
): Promise<string> {
  const blob = await createCroppedImage(sourceUrl, crop);
  const path = `telegram/${Date.now()}-${Math.random().toString(36).slice(2, 8)}.jpg`;
  const bucket = supabase.storage.from("deal-images");
  const { error } = await bucket.upload(path, blob, {
    cacheControl: "3600",
    contentType: OUTPUT_TYPE,
    upsert: false,
  });
  if (error) throw new Error(`No se pudo guardar el recorte: ${error.message}`);

  const {
    data: { publicUrl },
  } = bucket.getPublicUrl(path);
  return publicUrl;
}
