/** Estado de las imágenes de una propuesta: subidas en paralelo (máx. 3 a la
 *  vez), límite de 8 (incluidas las precargadas de Amazon) y 5 MB por fichero
 *  comprobados en cliente. La portada es siempre la primera imagen subida. */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { ApiError } from "@/services/api/client";
import { submissionsApi, type UploadedImage } from "@/services/api/submissions";

export const MAX_IMAGES = 8;
export const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const CONCURRENCY = 3;

export interface UploadItem {
  id: string;
  url?: string;
  previewUrl: string;
  status: "uploading" | "done" | "error";
  error?: string;
}

interface Job {
  id: string;
  run: () => Promise<UploadedImage>;
}

let seq = 0;
const nextId = () => `img-${++seq}`;

function uploadErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 413) return "La imagen supera 5 MB";
    if (error.status === 429) return error.message || "Demasiadas subidas, espera un momento";
    if (error.status === 400 && error.message) return error.message;
  }
  return "No se pudo subir la imagen";
}

export function useImageUploads(initial: string[]) {
  const [images, setImages] = useState<UploadItem[]>(() =>
    Array.from(new Set(initial.filter(Boolean)))
      .slice(0, MAX_IMAGES)
      .map((url) => ({ id: nextId(), url, previewUrl: url, status: "done" as const })),
  );
  const [announcement, setAnnouncement] = useState("");
  const itemsRef = useRef(images);
  const sources = useRef(new Map<string, string>());
  const objectUrls = useRef(new Map<string, string>());
  const queue = useRef<Job[]>([]);
  const active = useRef(0);
  const mounted = useRef(true);

  const commit = useCallback((update: (items: UploadItem[]) => UploadItem[]) => {
    itemsRef.current = update(itemsRef.current);
    if (mounted.current) setImages(itemsRef.current);
  }, []);

  useEffect(() => {
    mounted.current = true;
    const urls = objectUrls.current;
    return () => {
      mounted.current = false;
      queue.current = [];
      urls.forEach((u) => URL.revokeObjectURL(u));
      urls.clear();
    };
  }, []);

  const pump = useCallback(() => {
    while (active.current < CONCURRENCY && queue.current.length > 0) {
      const job = queue.current.shift()!;
      if (!itemsRef.current.some((i) => i.id === job.id)) continue;
      active.current += 1;
      job
        .run()
        .then((res) => {
          if (!itemsRef.current.some((i) => i.id === job.id)) return;
          commit((items) =>
            items.map((i) => (i.id === job.id ? { ...i, status: "done", url: res.url } : i)),
          );
          if (mounted.current) setAnnouncement("Imagen añadida");
        })
        .catch((error: unknown) => {
          const message = uploadErrorMessage(error);
          commit((items) =>
            items.map((i) => (i.id === job.id ? { ...i, status: "error", error: message } : i)),
          );
          if (mounted.current) setAnnouncement(`No se pudo añadir la imagen: ${message}`);
        })
        .finally(() => {
          active.current -= 1;
          if (mounted.current) pump();
        });
    }
  }, [commit]);

  const takeSlots = useCallback(<T>(candidates: T[]): T[] => {
    const free = MAX_IMAGES - itemsRef.current.length;
    if (candidates.length > free) toast.error(`Máximo ${MAX_IMAGES} imágenes por chollo`);
    return candidates.slice(0, Math.max(free, 0));
  }, []);

  const enqueue = useCallback(
    (entries: { item: UploadItem; run: () => Promise<UploadedImage> }[]) => {
      if (!entries.length) return;
      commit((items) => [...items, ...entries.map((e) => e.item)]);
      queue.current.push(...entries.map((e) => ({ id: e.item.id, run: e.run })));
      setAnnouncement(
        entries.length === 1 ? "Subiendo 1 imagen" : `Subiendo ${entries.length} imágenes`,
      );
      pump();
    },
    [commit, pump],
  );

  const addFiles = useCallback(
    (input: FileList | File[]) => {
      const valid = Array.from(input).filter((file) => {
        if (!file.type.startsWith("image/")) {
          toast.error(`"${file.name}" no es una imagen`);
          return false;
        }
        if (file.size > MAX_IMAGE_BYTES) {
          toast.error(`"${file.name || "La imagen"}" supera 5 MB`);
          return false;
        }
        return true;
      });
      enqueue(
        takeSlots(valid).map((file) => {
          const id = nextId();
          const previewUrl = URL.createObjectURL(file);
          objectUrls.current.set(id, previewUrl);
          return {
            item: { id, previewUrl, status: "uploading" as const },
            run: () => submissionsApi.uploadImage(file, file.name || "imagen.png"),
          };
        }),
      );
    },
    [enqueue, takeSlots],
  );

  const addUrls = useCallback(
    (urls: string[]) => {
      const known = new Set<string>([
        ...itemsRef.current.map((i) => i.url ?? ""),
        ...sources.current.values(),
      ]);
      const fresh = Array.from(new Set(urls.map((u) => u.trim()))).filter(
        (u) => u && !known.has(u),
      );
      enqueue(
        takeSlots(fresh).map((url) => {
          const id = nextId();
          sources.current.set(id, url);
          return {
            item: { id, previewUrl: url, status: "uploading" as const },
            run: () => submissionsApi.importImageUrl(url),
          };
        }),
      );
    },
    [enqueue, takeSlots],
  );

  const remove = useCallback(
    (id: string) => {
      const objectUrl = objectUrls.current.get(id);
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      objectUrls.current.delete(id);
      sources.current.delete(id);
      queue.current = queue.current.filter((job) => job.id !== id);
      commit((items) => items.filter((i) => i.id !== id));
      setAnnouncement("Imagen quitada");
    },
    [commit],
  );

  const move = useCallback(
    (id: string, dir: -1 | 1) => {
      commit((items) => {
        const from = items.findIndex((i) => i.id === id);
        const to = from + dir;
        if (from < 0 || to < 0 || to >= items.length) return items;
        const next = [...items];
        [next[from], next[to]] = [next[to]!, next[from]!];
        return next;
      });
    },
    [commit],
  );

  const setCover = useCallback(
    (id: string) => {
      commit((items) => {
        const item = items.find((i) => i.id === id);
        return item ? [item, ...items.filter((i) => i.id !== id)] : items;
      });
      setAnnouncement("Portada actualizada");
    },
    [commit],
  );

  const urls = useMemo(
    () => images.filter((i) => i.status === "done" && i.url).map((i) => i.url!),
    [images],
  );

  return {
    images,
    urls,
    cover: urls[0] ?? null,
    isUploading: images.some((i) => i.status === "uploading"),
    hasErrors: images.some((i) => i.status === "error"),
    announcement,
    addFiles,
    addUrls,
    remove,
    move,
    setCover,
  };
}

export type ImageUploads = ReturnType<typeof useImageUploads>;
