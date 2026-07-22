import type { User } from "@supabase/supabase-js";

function metadataValue(metadata: Record<string, unknown> | undefined, keys: string[]): string {
  if (!metadata) return "";
  for (const key of keys) {
    const value = metadata[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return "";
}

function identityData(user: User | null): Record<string, unknown> | undefined {
  const data = user?.identities?.[0]?.identity_data;
  return data && typeof data === "object" ? (data as Record<string, unknown>) : undefined;
}

function emailName(email?: string | null): string {
  return email?.split("@")[0]?.trim() ?? "";
}

export function googleDisplayName(user: User | null, fallback = ""): string {
  return (
    metadataValue(user?.user_metadata as Record<string, unknown> | undefined, [
      "display_name",
      "full_name",
      "name",
      "preferred_username",
    ]) ||
    metadataValue(identityData(user), [
      "display_name",
      "full_name",
      "name",
      "preferred_username",
    ]) ||
    fallback ||
    emailName(user?.email)
  );
}

export function googleAvatarUrl(user: User | null, fallback = ""): string {
  return (
    metadataValue(user?.user_metadata as Record<string, unknown> | undefined, [
      "avatar_url",
      "picture",
    ]) ||
    metadataValue(identityData(user), ["avatar_url", "picture"]) ||
    fallback
  );
}

/** True si el usuario entró (al menos una vez) con Google. Estas cuentas no
 * pueden cambiar su email desde aquí (lo gestiona Google). */
export function isGoogleLinkedAccount(user: User | null): boolean {
  return (
    user?.app_metadata?.provider === "google" ||
    (user?.identities ?? []).some((identity) => identity.provider === "google")
  );
}
