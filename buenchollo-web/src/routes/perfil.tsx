import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Layout } from "@/components/layout/Layout";
import { useAuth } from "@/hooks/useAuth";
import { removeStoredAvatar, uploadAvatar } from "@/lib/avatar-upload";
import { googleAvatarUrl, googleDisplayName } from "@/lib/google-profile";
import { authApi } from "@/services/api/auth";
import { errorMessage } from "@/lib/errors";
import { toast } from "sonner";
import { Camera, Download, Lock, LogOut, Mail, Save, Trash2, User as UserIcon } from "lucide-react";

export const Route = createFileRoute("/perfil")({
  component: ProfilePage,
  head: () => ({
    meta: [
      { title: "Mi perfil · BuenChollo Tech" },
      { name: "description", content: "Ajustes de tu cuenta de BuenChollo Tech." },
      { property: "og:title", content: "Mi perfil · BuenChollo Tech" },
      { property: "og:description", content: "Ajustes de tu cuenta de BuenChollo Tech." },
      { property: "og:url", content: "https://buenchollotech.com/perfil" },
      { name: "robots", content: "noindex, nofollow" },
    ],
    links: [{ rel: "canonical", href: "https://buenchollotech.com/perfil" }],
  }),
});

function ProfilePage() {
  const { user, me, loading: authLoading, refreshMe, signOut } = useAuth();
  const nav = useNavigate();
  const [name, setName] = useState("");
  const [bio, setBio] = useState("");
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const googleName = googleDisplayName(user);
  const googleAvatar = googleAvatarUrl(user) || null;

  useEffect(() => {
    if (!authLoading && !user) nav({ to: "/login" });
  }, [authLoading, user, nav]);

  useEffect(() => {
    if (!user) return;

    // `me` ya viene cargado desde useAuth (mismo dato guardado en BD que
    // getMyProfile) antes de que authLoading pase a false, así que evita
    // pintar primero el avatar de Google mientras llega la respuesta.
    setName(me?.display_name?.trim() || googleName);
    setAvatarUrl(me?.avatar_url || googleAvatar);

    authApi
      .getMyProfile()
      .then((profile) => {
        setName(profile.display_name?.trim() || googleName);
        setBio(profile.bio ?? "");
        setAvatarUrl(profile.avatar_url || googleAvatar);
      })
      .catch(() => {
        // bio queda vacío si falla; name/avatarUrl ya están bien seteados por `me`.
      });
  }, [googleAvatar, googleName, me, user]);

  const persistProfile = async (
    nextAvatarUrl = avatarUrl,
    successMessage = "Perfil actualizado",
    showError = true,
  ) => {
    if (!user) return;
    const displayName = name.trim();
    if (displayName.length < 2) {
      toast.error("El nombre visible debe tener al menos 2 caracteres");
      return;
    }

    setSaving(true);
    try {
      await authApi.updateMyProfile({
        display_name: displayName.slice(0, 50),
        bio: bio.slice(0, 300),
        avatar_url: nextAvatarUrl,
      });
      await refreshMe();
      toast.success(successMessage);
    } catch (e: unknown) {
      if (showError) toast.error(errorMessage(e, "Error al guardar"));
      throw e;
    } finally {
      setSaving(false);
    }
  };

  const save = () => {
    void persistProfile();
  };

  const handleAvatarFile = async (files: FileList | null) => {
    const file = files?.[0];
    if (!user || !file) return;

    const previousAvatarUrl = avatarUrl;
    let uploadedAvatarUrl: string | null = null;
    setAvatarUploading(true);
    try {
      const nextAvatarUrl = await uploadAvatar(user.id, file);
      uploadedAvatarUrl = nextAvatarUrl;
      setAvatarUrl(nextAvatarUrl);
      await persistProfile(nextAvatarUrl, "Avatar actualizado", false);
      if (previousAvatarUrl && previousAvatarUrl !== nextAvatarUrl) {
        void removeStoredAvatar(previousAvatarUrl);
      }
    } catch (e: unknown) {
      setAvatarUrl(previousAvatarUrl);
      if (uploadedAvatarUrl) void removeStoredAvatar(uploadedAvatarUrl);
      toast.error(errorMessage(e, "Error al subir el avatar"));
    } finally {
      setAvatarUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const removeAvatar = async () => {
    const previousAvatarUrl = avatarUrl;
    setAvatarUrl(null);
    try {
      await persistProfile(null, "Avatar quitado", false);
      if (previousAvatarUrl) void removeStoredAvatar(previousAvatarUrl);
    } catch (e: unknown) {
      setAvatarUrl(previousAvatarUrl);
      toast.error(errorMessage(e, "Error al quitar el avatar"));
    }
  };

  const pendingAction = () => {
    toast.info("Esta opción se conectará en una siguiente iteración");
  };

  return (
    <Layout>
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:py-10">
        <div className="mb-8">
          <div className="mb-2 font-mono text-xs text-cyan-glow">&gt; MI_PERFIL</div>
          <h1 className="text-3xl font-bold tracking-tight">Perfil</h1>
        </div>

        <section className="divide-y divide-surface-700 border-y border-surface-700">
          <div className="grid gap-6 py-8 md:grid-cols-[220px_1fr]">
            <div>
              <h2 className="text-lg font-bold">Tu avatar</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {avatarUrl ? "Imagen actual del perfil" : "Sin avatar configurado"}
              </p>
            </div>
            <div className="flex flex-col items-center gap-5">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                className="hidden"
                onChange={(event) => void handleAvatarFile(event.currentTarget.files)}
              />
              <div className="flex size-40 items-center justify-center overflow-hidden rounded-full border border-surface-600 bg-surface-800 sm:size-52">
                {avatarUrl ? (
                  <img
                    src={avatarUrl}
                    alt=""
                    className="size-full object-cover"
                    referrerPolicy="no-referrer"
                    onError={() => setAvatarUrl(null)}
                  />
                ) : (
                  <UserIcon className="size-16 text-cyan-glow" />
                )}
              </div>
              <div className="grid w-full max-w-md gap-3 sm:grid-cols-[1fr_auto]">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={avatarUploading || saving}
                  className="inline-flex items-center justify-center gap-2 rounded-full border border-surface-600 px-5 py-2.5 font-mono text-xs font-bold transition-colors hover:border-cyan-glow hover:text-cyan-glow disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Camera className="size-4" />
                  {avatarUploading ? "SUBIENDO..." : "REEMPLAZAR"}
                </button>
                <button
                  type="button"
                  onClick={() => void removeAvatar()}
                  disabled={!avatarUrl || avatarUploading || saving}
                  className="inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 font-mono text-xs font-bold text-alert-red transition-colors hover:bg-alert-red/10 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Trash2 className="size-4" />
                  QUITAR
                </button>
              </div>
              <p className="text-center text-sm text-muted-foreground">
                Para resultados óptimos utiliza una imagen cuadrada.
              </p>
            </div>
          </div>

          <div className="grid gap-4 py-7 md:grid-cols-[220px_1fr]">
            <h2 className="text-lg font-bold">Tu nombre visible</h2>
            <div className="space-y-3">
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={50}
                className="w-full border border-surface-600 bg-surface-900 px-4 py-3 font-mono text-sm text-cyan-glow outline-none transition-colors focus:border-cyan-glow"
              />
              <button
                type="button"
                onClick={save}
                disabled={saving}
                className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-surface-600 px-5 py-3 font-mono text-xs font-bold transition-colors hover:border-cyan-glow hover:text-cyan-glow disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Save className="size-4" />
                {saving ? "GUARDANDO..." : "GUARDAR NOMBRE VISIBLE"}
              </button>
              <p className="text-sm text-muted-foreground">
                Este nombre aparecerá en tus comentarios y actividad pública.
              </p>
            </div>
          </div>

          <div className="grid gap-4 py-7 md:grid-cols-[220px_1fr]">
            <h2 className="text-lg font-bold">¿Tienes algo que decir?</h2>
            <div className="space-y-3">
              <textarea
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                maxLength={300}
                rows={4}
                placeholder="Cuéntale algo a la comunidad..."
                className="w-full resize-y border border-surface-600 bg-surface-900 px-4 py-3 text-sm outline-none transition-colors focus:border-cyan-glow"
              />
              <button
                type="button"
                onClick={save}
                disabled={saving}
                className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-surface-600 px-5 py-3 font-mono text-xs font-bold transition-colors hover:border-cyan-glow hover:text-cyan-glow disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Save className="size-4" />
                {saving ? "GUARDANDO..." : "GUARDAR DESCRIPCIÓN"}
              </button>
            </div>
          </div>

          <div className="grid gap-4 py-7 md:grid-cols-[220px_1fr]">
            <h2 className="text-lg font-bold">Tu email</h2>
            <div className="space-y-3">
              <p className="flex items-center gap-2 font-mono text-sm text-cyan-glow">
                <Mail className="size-4" />
                {user?.email}
              </p>
              <button
                type="button"
                onClick={pendingAction}
                className="inline-flex w-full items-center justify-center rounded-full border border-surface-600 px-5 py-3 font-mono text-xs font-bold transition-colors hover:border-cyan-glow hover:text-cyan-glow"
              >
                CAMBIAR EMAIL
              </button>
            </div>
          </div>

          <div className="grid gap-4 py-7 md:grid-cols-[220px_1fr]">
            <h2 className="text-lg font-bold">Tu contraseña</h2>
            <div className="space-y-3">
              <p className="flex items-center gap-2 font-mono text-sm text-cyan-glow">
                <Lock className="size-4" />
                ••••••••
              </p>
              <button
                type="button"
                onClick={pendingAction}
                className="inline-flex w-full items-center justify-center rounded-full border border-surface-600 px-5 py-3 font-mono text-xs font-bold transition-colors hover:border-cyan-glow hover:text-cyan-glow"
              >
                CAMBIAR CONTRASEÑA
              </button>
            </div>
          </div>

          <div className="grid gap-4 py-7 md:grid-cols-[220px_1fr]">
            <h2 className="text-lg font-bold">Datos de la cuenta</h2>
            <button
              type="button"
              onClick={pendingAction}
              className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-surface-600 px-5 py-3 font-mono text-xs font-bold transition-colors hover:border-cyan-glow hover:text-cyan-glow"
            >
              <Download className="size-4" />
              GENERAR DATOS
            </button>
          </div>

          <div className="grid gap-4 py-7 md:grid-cols-[220px_1fr]">
            <h2 className="text-lg font-bold">Sesión</h2>
            <button
              type="button"
              onClick={signOut}
              className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-surface-600 px-5 py-3 font-mono text-xs font-bold transition-colors hover:border-alert-red hover:text-alert-red"
            >
              <LogOut className="size-4" />
              CERRAR SESIÓN
            </button>
          </div>

          <div className="grid gap-4 py-7 md:grid-cols-[220px_1fr]">
            <h2 className="text-lg font-bold">Eliminar cuenta</h2>
            <button
              type="button"
              onClick={pendingAction}
              className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-alert-red px-5 py-3 font-mono text-xs font-bold text-alert-red transition-colors hover:bg-alert-red/10"
            >
              <Trash2 className="size-4" />
              ELIMINAR CUENTA
            </button>
          </div>
        </section>
      </div>
    </Layout>
  );
}
