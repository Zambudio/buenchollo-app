/** Subida de imágenes del blog a Supabase Storage (excepción aprobada
 * ADR-002), bucket dedicado `blog-images` — nunca reutiliza `deal-images`.
 * Mismo patrón que `features/admin/hooks/useDealImages.ts`. */
import { useState } from "react";
import { toast } from "sonner";

const MAX_SIZE_BYTES = 5 * 1024 * 1024;
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/avif"];

export function useBlogImages(userId: string | undefined, postId: string) {
  const [uploading, setUploading] = useState(false);

  const uploadImage = async (file: File): Promise<string | null> => {
    if (!userId) {
      toast.error("Debes iniciar sesión");
      return null;
    }
    if (!ALLOWED_TYPES.includes(file.type)) {
      toast.error(`${file.name}: formato no permitido (jpg, png, webp o avif)`);
      return null;
    }
    if (file.size > MAX_SIZE_BYTES) {
      toast.error(`${file.name}: máx 5MB`);
      return null;
    }
    setUploading(true);
    try {
      const { supabase } = await import("@/integrations/supabase/client");
      const ext = file.name.split(".").pop() ?? "jpg";
      const path = `${userId}/${postId}/${Date.now()}-${Math.random().toString(36).slice(2, 8)}.${ext}`;
      const { error } = await supabase.storage.from("blog-images").upload(path, file);
      if (error) {
        toast.error(error.message);
        return null;
      }
      const {
        data: { publicUrl },
      } = supabase.storage.from("blog-images").getPublicUrl(path);
      return publicUrl;
    } finally {
      setUploading(false);
    }
  };

  return { uploading, uploadImage };
}
