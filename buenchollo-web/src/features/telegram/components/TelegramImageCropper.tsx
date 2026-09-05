import { useEffect, useRef, useState, type PointerEvent } from "react";
import { Crop, Loader2, RotateCcw, X } from "lucide-react";

import type { CropArea } from "../image-crop";

interface Point {
  x: number;
  y: number;
}

interface TelegramImageCropperProps {
  imageUrl: string;
  saving: boolean;
  onAccept: (crop: CropArea) => void;
  onCancel: () => void;
}

const MIN_CROP_SIZE = 0.02;

function cropFromPoints(start: Point, end: Point): CropArea {
  return {
    x: Math.min(start.x, end.x),
    y: Math.min(start.y, end.y),
    width: Math.abs(end.x - start.x),
    height: Math.abs(end.y - start.y),
  };
}

export function TelegramImageCropper({
  imageUrl,
  saving,
  onAccept,
  onCancel,
}: TelegramImageCropperProps) {
  const selectionLayerRef = useRef<HTMLDivElement>(null);
  const dragStartRef = useRef<Point | null>(null);
  const [crop, setCrop] = useState<CropArea | null>(null);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !saving) onCancel();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onCancel, saving]);

  const pointFromEvent = (event: PointerEvent<HTMLDivElement>): Point => {
    const rect = selectionLayerRef.current?.getBoundingClientRect();
    if (!rect || rect.width === 0 || rect.height === 0) return { x: 0, y: 0 };
    return {
      x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)),
      y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height)),
    };
  };

  const handlePointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (saving) return;
    const start = pointFromEvent(event);
    dragStartRef.current = start;
    setCrop({ x: start.x, y: start.y, width: 0, height: 0 });
    event.preventDefault();
    event.currentTarget.setPointerCapture?.(event.pointerId);
  };

  const handlePointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (!dragStartRef.current) return;
    setCrop(cropFromPoints(dragStartRef.current, pointFromEvent(event)));
  };

  const finishSelection = (event: PointerEvent<HTMLDivElement>) => {
    if (!dragStartRef.current) return;
    const nextCrop = cropFromPoints(dragStartRef.current, pointFromEvent(event));
    dragStartRef.current = null;
    if (nextCrop.width >= MIN_CROP_SIZE && nextCrop.height >= MIN_CROP_SIZE) {
      setCrop(nextCrop);
    } else {
      setCrop(null);
    }
  };

  const isValid = crop !== null && crop.width >= MIN_CROP_SIZE && crop.height >= MIN_CROP_SIZE;

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center bg-black/85 p-3 backdrop-blur-sm sm:p-6"
      onPointerDown={(event) => {
        if (event.target === event.currentTarget && !saving) onCancel();
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="telegram-crop-title"
        className="flex max-h-[calc(100vh-1.5rem)] w-full max-w-4xl flex-col border border-surface-700 bg-surface-800 shadow-2xl sm:max-h-[calc(100vh-3rem)]"
      >
        <header className="flex shrink-0 items-center justify-between border-b border-surface-700 px-4 py-3 sm:px-5">
          <div className="flex items-center gap-2">
            <Crop className="size-4 text-cyan-glow" />
            <h2
              id="telegram-crop-title"
              className="font-mono text-xs font-bold uppercase text-cyan-glow sm:text-sm"
            >
              Recortar imagen
            </h2>
          </div>
          <button
            type="button"
            aria-label="Cancelar recorte"
            onClick={onCancel}
            disabled={saving}
            className="p-2 text-muted-foreground transition-colors hover:text-alert-red focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-cyan-glow disabled:opacity-40"
          >
            <X className="size-4" />
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-auto bg-surface-900 p-3 sm:p-5">
          <p className="mb-3 text-center font-mono text-[10px] uppercase text-muted-foreground sm:text-xs">
            Arrastra sobre la imagen para seleccionar la zona que quieres publicar
          </p>
          <div className="flex min-h-56 items-center justify-center overflow-hidden">
            <div className="relative inline-flex max-w-full">
              <img
                src={imageUrl}
                alt="Imagen que se va a recortar"
                draggable={false}
                className="block max-h-[58vh] max-w-full select-none object-contain"
              />
              <div
                ref={selectionLayerRef}
                data-testid="crop-selection-layer"
                className="absolute inset-0 cursor-crosshair touch-none overflow-hidden"
                onPointerDown={handlePointerDown}
                onPointerMove={handlePointerMove}
                onPointerUp={finishSelection}
                onPointerCancel={finishSelection}
              >
                {crop && isValid && (
                  <div
                    className="pointer-events-none absolute border-2 border-cyan-glow shadow-[0_0_0_9999px_rgba(0,0,0,0.62)]"
                    style={{
                      left: `${crop.x * 100}%`,
                      top: `${crop.y * 100}%`,
                      width: `${crop.width * 100}%`,
                      height: `${crop.height * 100}%`,
                    }}
                  >
                    <span className="absolute -left-1 -top-1 size-2 border border-surface-900 bg-cyan-glow" />
                    <span className="absolute -right-1 -top-1 size-2 border border-surface-900 bg-cyan-glow" />
                    <span className="absolute -bottom-1 -left-1 size-2 border border-surface-900 bg-cyan-glow" />
                    <span className="absolute -bottom-1 -right-1 size-2 border border-surface-900 bg-cyan-glow" />
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        <footer className="flex shrink-0 flex-col gap-2 border-t border-surface-700 p-3 sm:flex-row sm:items-center sm:justify-between sm:px-5 sm:py-4">
          <button
            type="button"
            onClick={() => setCrop(null)}
            disabled={saving || !crop}
            className="flex min-h-10 items-center justify-center gap-2 border border-surface-700 px-4 font-mono text-xs uppercase text-muted-foreground transition-colors hover:border-cyan-glow hover:text-cyan-glow focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-cyan-glow disabled:opacity-40"
          >
            <RotateCcw className="size-3.5" />
            Restablecer
          </button>
          <div className="grid grid-cols-2 gap-2 sm:flex">
            <button
              type="button"
              onClick={onCancel}
              disabled={saving}
              className="min-h-10 border border-surface-700 px-5 font-mono text-xs font-bold uppercase transition-colors hover:border-alert-red hover:text-alert-red focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-cyan-glow disabled:opacity-40"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={() => crop && onAccept(crop)}
              disabled={!isValid || saving}
              className="flex min-h-10 items-center justify-center gap-2 bg-cyan-glow px-5 font-mono text-xs font-bold uppercase text-surface-900 transition-colors hover:bg-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-glow focus-visible:ring-offset-2 focus-visible:ring-offset-surface-800 disabled:opacity-50"
            >
              {saving && <Loader2 className="size-4 animate-spin" />}
              {saving ? "Guardando..." : "Aceptar recorte"}
            </button>
          </div>
        </footer>
      </section>
    </div>
  );
}
