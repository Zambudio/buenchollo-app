import { supabase } from "@/integrations/supabase/client";

export const AVATAR_BUCKET = "avatars";
export const AVATAR_MAX_BYTES = 5 * 1024 * 1024;
export const AVATAR_ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"];

export function validateAvatarFile(file: File): string | null {
  if (!AVATAR_ALLOWED_TYPES.includes(file.type)) {
    return "El avatar debe ser JPG, PNG, WEBP o GIF";
  }
  if (file.size > AVATAR_MAX_BYTES) {
    return "El avatar no puede superar 5MB";
  }
  return null;
}

export function avatarPathFromPublicUrl(publicUrl: string | null | undefined): string | null {
  if (!publicUrl) return null;
  try {
    const { pathname } = new URL(publicUrl);
    const marker = `/storage/v1/object/public/${AVATAR_BUCKET}/`;
    const markerIndex = pathname.indexOf(marker);
    if (markerIndex === -1) return null;
    return decodeURIComponent(pathname.slice(markerIndex + marker.length));
  } catch {
    return null;
  }
}

function extensionFor(file: File): string {
  const byType: Record<string, string> = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
  };
  return byType[file.type] ?? "png";
}

export async function uploadAvatar(userId: string, file: File): Promise<string> {
  const validationError = validateAvatarFile(file);
  if (validationError) throw new Error(validationError);

  const path = `${userId}/avatar-${Date.now()}-${Math.random()
    .toString(36)
    .slice(2, 8)}.${extensionFor(file)}`;

  const { error } = await supabase.storage.from(AVATAR_BUCKET).upload(path, file, {
    cacheControl: "3600",
    contentType: file.type,
    upsert: false,
  });
  if (error) throw error;

  const {
    data: { publicUrl },
  } = supabase.storage.from(AVATAR_BUCKET).getPublicUrl(path);

  return publicUrl;
}

export async function removeStoredAvatar(publicUrl: string | null | undefined): Promise<void> {
  const path = avatarPathFromPublicUrl(publicUrl);
  if (!path) return;
  await supabase.storage.from(AVATAR_BUCKET).remove([path]);
}
