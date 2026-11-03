import { useEffect, useId, useRef, useState } from "react";
import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  ClipboardPaste,
  ImagePlus,
  Loader2,
  Star,
  X,
} from "lucide-react";
import { toast } from "sonner";
import {
  canReadClipboard,
  extractClipboardItems,
  hasPlainText,
  isTextEntryElement,
  readClipboardImages,
} from "../lib/clipboard";
import { MAX_IMAGES, useImageUploads } from "../hooks/useImageUploads";

export interface ImageUploaderState {
  images: string[];
  cover: string | null;
  isUploading: boolean;
  hasErrors: boolean;
}

interface ImageUploaderProps {
  initial?: string[];
  onChange: (state: ImageUploaderState) => void;
}

const iconBtn =
  "flex-1 inline-flex items-center justify-center h-9 text-muted-foreground hover:text-cyan-glow hover:bg-surface-700 disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-muted-foreground transition-colors focus-visible:outline-2 focus-visible:outline-cyan-glow";

export function ImageUploader({ initial = [], onChange }: ImageUploaderProps) {
  const uploads = useImageUploads(initial);
  const { images, urls, cover, isUploading, hasErrors, addFiles, addUrls } = uploads;
  const ids = useId();
  const [dragging, setDragging] = useState(false);
  const dragDepth = useRef(0);
  const [imageUrl, setImageUrl] = useState("");
  const [canPaste, setCanPaste] = useState(false);

  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  useEffect(() => {
    onChangeRef.current({ images: urls, cover, isUploading, hasErrors });
  }, [urls, cover, isUploading, hasErrors]);

  useEffect(() => {
    setCanPaste(canReadClipboard());
  }, []);

  useEffect(() => {
    // Pegado global mientras el paso 2 está montado. Regla: si el foco está en
    // un campo de texto y el portapapeles trae texto, se deja pegar el texto y
    // no se toca nada (aunque también traiga imagen). Fuera de un campo de
    // texto, o si solo hay imagen, nos quedamos con imágenes/URL de imagen.
    // El texto normal nunca se intercepta (no hay preventDefault).
    const onPaste = (e: ClipboardEvent) => {
      if (isTextEntryElement(document.activeElement) && hasPlainText(e)) return;
      const { files, urls: pastedUrls } = extractClipboardItems(e);
      if (!files.length && !pastedUrls.length) return;
      e.preventDefault();
      if (files.length) addFiles(files);
      if (pastedUrls.length) addUrls(pastedUrls);
    };
    document.addEventListener("paste", onPaste);
    return () => document.removeEventListener("paste", onPaste);
  }, [addFiles, addUrls]);

  const pasteFromClipboard = async () => {
    try {
      const { files, urls: pastedUrls } = await readClipboardImages(navigator.clipboard);
      if (!files.length && !pastedUrls.length) {
        toast.info("No hay ninguna imagen en el portapapeles");
        return;
      }
      if (files.length) addFiles(files);
      if (pastedUrls.length) addUrls(pastedUrls);
    } catch {
      toast.error("No se pudo leer el portapapeles. Permite el acceso o pega con Ctrl+V.");
    }
  };

  const addImageUrl = () => {
    const value = imageUrl.trim();
    if (!/^https?:\/\/\S+$/i.test(value)) {
      toast.error("Introduce una URL de imagen válida (http o https)");
      return;
    }
    addUrls([value]);
    setImageUrl("");
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    dragDepth.current = 0;
    setDragging(false);
    const { files, urls: droppedUrls } = extractClipboardItems(e.dataTransfer);
    if (files.length) addFiles(files);
    if (droppedUrls.length) addUrls(droppedUrls);
    if (!files.length && !droppedUrls.length) toast.error("Eso no parece una imagen");
  };

  const full = images.length >= MAX_IMAGES;
  const helpId = `${ids}-help`;
  const fileId = `${ids}-file`;
  const urlId = `${ids}-url`;

  return (
    <section aria-labelledby={`${ids}-title`} className="space-y-3">
      <div className="flex items-baseline justify-between gap-2">
        <h2 id={`${ids}-title`} className="text-xs font-mono uppercase text-muted-foreground">
          Imágenes
        </h2>
        <span className="font-mono text-xs text-muted-foreground tabular-nums">
          {images.length}/{MAX_IMAGES}
        </span>
      </div>

      <div
        role="group"
        aria-describedby={helpId}
        data-testid="image-dropzone"
        onDragEnter={(e) => {
          e.preventDefault();
          dragDepth.current += 1;
          setDragging(true);
        }}
        onDragOver={(e) => {
          e.preventDefault();
          e.dataTransfer.dropEffect = "copy";
        }}
        onDragLeave={() => {
          dragDepth.current = Math.max(0, dragDepth.current - 1);
          if (dragDepth.current === 0) setDragging(false);
        }}
        onDrop={onDrop}
        className={`flex flex-col items-center gap-3 border-2 border-dashed px-4 py-6 text-center transition-colors ${
          dragging ? "border-cyan-glow bg-cyan-glow/10" : "border-surface-600 bg-surface-900"
        }`}
      >
        <ImagePlus className="size-7 text-cyan-glow" aria-hidden="true" />
        <div>
          <p id={helpId} className="text-sm">
            Arrastra, pega (Ctrl+V) o elige imágenes
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            JPG, PNG, WebP o GIF · máx. 5 MB · hasta {MAX_IMAGES}
          </p>
        </div>
        <div className="flex flex-wrap justify-center gap-2">
          <input
            id={fileId}
            type="file"
            accept="image/*"
            multiple
            disabled={full}
            className="peer sr-only"
            onChange={(e) => {
              if (e.target.files) addFiles(e.target.files);
              e.target.value = "";
            }}
          />
          <label
            htmlFor={fileId}
            className="inline-flex items-center gap-2 cursor-pointer bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2.5 hover:bg-foreground transition-colors peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-cyan-glow peer-disabled:opacity-50 peer-disabled:cursor-not-allowed"
          >
            <ImagePlus className="size-4" aria-hidden="true" />
            Elegir imágenes
          </label>
          {canPaste && (
            <button
              type="button"
              onClick={() => void pasteFromClipboard()}
              disabled={full}
              className="inline-flex items-center gap-2 border border-surface-600 bg-surface-800 font-mono text-xs font-bold px-4 py-2.5 hover:border-cyan-glow transition-colors disabled:opacity-50"
            >
              <ClipboardPaste className="size-4" aria-hidden="true" />
              Pegar
            </button>
          )}
        </div>
      </div>

      <div>
        <label htmlFor={urlId} className="block text-xs font-mono text-muted-foreground mb-1">
          O añade una imagen por URL
        </label>
        <div className="flex gap-2">
          <input
            id={urlId}
            type="url"
            inputMode="url"
            autoComplete="off"
            value={imageUrl}
            disabled={full}
            onChange={(e) => setImageUrl(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addImageUrl();
              }
            }}
            placeholder="https://…/imagen.jpg"
            className="min-w-0 flex-1 bg-surface-900 border border-surface-700 px-3 py-2 text-sm font-mono outline-none focus:border-cyan-glow"
          />
          <button
            type="button"
            onClick={addImageUrl}
            disabled={full || !imageUrl.trim()}
            className="shrink-0 border border-surface-600 bg-surface-800 font-mono text-xs font-bold px-4 hover:border-cyan-glow transition-colors disabled:opacity-50"
          >
            Añadir
          </button>
        </div>
      </div>

      {images.length > 0 && (
        <ul aria-label="Imágenes añadidas" className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {images.map((item, index) => {
            const isCover = index === 0 && item.status === "done";
            const errorId = `${ids}-err-${item.id}`;
            return (
              <li
                key={item.id}
                data-testid="image-item"
                data-url={item.url ?? ""}
                aria-describedby={item.status === "error" ? errorId : undefined}
                className={`flex flex-col border bg-surface-800 ${
                  item.status === "error" ? "border-alert-red" : "border-surface-700"
                }`}
              >
                <div className="relative aspect-square bg-white overflow-hidden">
                  <img
                    src={item.previewUrl}
                    alt={`Imagen ${index + 1}${isCover ? " (portada)" : ""}`}
                    className={`absolute inset-0 size-full object-contain p-1 ${
                      item.status === "done" ? "" : "opacity-40"
                    }`}
                  />
                  {item.status === "uploading" && (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <Loader2
                        className="size-6 animate-spin text-surface-900"
                        aria-hidden="true"
                      />
                      <span className="sr-only">Subiendo</span>
                    </div>
                  )}
                  {item.status === "error" && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center gap-1 bg-surface-900/80 p-2 text-center">
                      <AlertCircle className="size-5 text-alert-red" aria-hidden="true" />
                      <span id={errorId} className="text-[11px] leading-tight text-foreground">
                        {item.error}
                      </span>
                    </div>
                  )}
                  {isCover && (
                    <span className="absolute top-1 left-1 bg-cyan-glow text-surface-900 font-mono text-[10px] font-bold px-1.5 py-0.5">
                      PORTADA
                    </span>
                  )}
                </div>
                <div className="flex border-t border-surface-700">
                  <button
                    type="button"
                    aria-label="Mover a la izquierda"
                    disabled={index === 0}
                    onClick={() => uploads.move(item.id, -1)}
                    className={iconBtn}
                  >
                    <ChevronLeft className="size-4" aria-hidden="true" />
                  </button>
                  <button
                    type="button"
                    aria-label="Usar como portada"
                    aria-pressed={isCover}
                    disabled={isCover || item.status !== "done"}
                    onClick={() => uploads.setCover(item.id)}
                    className={iconBtn}
                  >
                    <Star
                      className={`size-4 ${isCover ? "fill-cyan-glow text-cyan-glow" : ""}`}
                      aria-hidden="true"
                    />
                  </button>
                  <button
                    type="button"
                    aria-label="Mover a la derecha"
                    disabled={index === images.length - 1}
                    onClick={() => uploads.move(item.id, 1)}
                    className={iconBtn}
                  >
                    <ChevronRight className="size-4" aria-hidden="true" />
                  </button>
                  <button
                    type="button"
                    aria-label="Quitar imagen"
                    onClick={() => uploads.remove(item.id)}
                    className={`${iconBtn} hover:!text-alert-red`}
                  >
                    <X className="size-4" aria-hidden="true" />
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {hasErrors && (
        <p className="text-xs text-alert-red">
          Quita las imágenes con error para poder enviar el chollo.
        </p>
      )}
      <p aria-live="polite" className="sr-only">
        {uploads.announcement}
      </p>
    </section>
  );
}
