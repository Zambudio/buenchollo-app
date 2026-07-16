/**
 * Gestión de imágenes del formulario de chollos: añadir por URL, subir a
 * Supabase Storage (excepción aprobada ADR-002), reordenar y eliminar.
 * Extraído de routes/admin.chollos.tsx (TD-03).
 */
import { useRef, useState, type Dispatch, type SetStateAction } from "react";
import { toast } from "sonner";
import type { DealForm } from "../deal-form";

export function useDealImages(
  form: DealForm,
  setForm: Dispatch<SetStateAction<DealForm>>,
  userId: string | undefined,
) {
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const addImageUrl = () => {
    const url = form.image_url.trim();
    if (!url) return;
    if (form.images.includes(url)) {
      setForm({ ...form, image_url: "" });
      return;
    }
    setForm({ ...form, images: [...form.images, url], image_url: "" });
  };

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0 || !userId) return;
    setUploading(true);
    const newUrls: string[] = [];
    const { supabase } = await import("@/integrations/supabase/client");
    for (const file of Array.from(files)) {
      if (!file.type.startsWith("image/")) {
        toast.error(`${file.name}: no es imagen`);
        continue;
      }
      if (file.size > 5 * 1024 * 1024) {
        toast.error(`${file.name}: máx 5MB`);
        continue;
      }
      const ext = file.name.split(".").pop();
      const path = `${userId}/${Date.now()}-${Math.random().toString(36).slice(2, 8)}.${ext}`;
      const { error } = await supabase.storage.from("deal-images").upload(path, file);
      if (error) {
        toast.error(error.message);
        continue;
      }
      const {
        data: { publicUrl },
      } = supabase.storage.from("deal-images").getPublicUrl(path);
      newUrls.push(publicUrl);
    }
    setForm((f) => ({ ...f, images: [...f.images, ...newUrls] }));
    setUploading(false);
    if (fileRef.current) fileRef.current.value = "";
    if (newUrls.length) toast.success(`${newUrls.length} imagen(es) subida(s)`);
  };

  const removeImage = (i: number) => {
    setForm({ ...form, images: form.images.filter((_, idx) => idx !== i) });
  };

  const moveImage = (i: number, dir: -1 | 1) => {
    const j = i + dir;
    if (j < 0 || j >= form.images.length) return;
    const arr = [...form.images];
    const a = arr[i];
    const b = arr[j];
    if (a === undefined || b === undefined) return; // guards para noUncheckedIndexedAccess
    arr[i] = b;
    arr[j] = a;
    setForm({ ...form, images: arr });
  };

  return { uploading, fileRef, addImageUrl, handleFiles, removeImage, moveImage };
}
