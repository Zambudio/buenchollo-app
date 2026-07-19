import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { User as UserIcon } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAuth } from "@/hooks/useAuth";
import { googleAvatarUrl, googleDisplayName } from "@/lib/google-profile";
import { authApi } from "@/services/api/auth";

export function WelcomeProfileDialog() {
  const { user, me, loading: authLoading, refreshMe } = useAuth();
  const [dismissed, setDismissed] = useState(false);
  const [devPreview, setDevPreview] = useState(false);
  const [devName, setDevName] = useState("");
  const [devAvatar, setDevAvatar] = useState("");
  const [profileNeedsOnboarding, setProfileNeedsOnboarding] = useState(false);
  const [name, setName] = useState("");
  const [bio, setBio] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [saving, setSaving] = useState(false);

  const googleName = useMemo(() => googleDisplayName(user, devName), [devName, user]);
  const googleAvatar = useMemo(() => googleAvatarUrl(user, devAvatar), [devAvatar, user]);

  useEffect(() => {
    if (!import.meta.env.DEV || typeof window === "undefined") return;

    const params = new URLSearchParams(window.location.search);
    const shouldPreview = params.get("welcomePreview") === "1";
    if (!shouldPreview) return;

    setDevPreview(true);
    setDevName(params.get("name")?.trim() || "Usuario Google");
    setDevAvatar(params.get("avatar")?.trim() || "");
  }, []);

  const open = Boolean(
    !dismissed &&
    ((!authLoading && user && (me?.needs_onboarding || profileNeedsOnboarding)) || devPreview),
  );

  useEffect(() => {
    if (!user && !devPreview) return;
    let cancelled = false;

    setName(googleName);
    setAvatarUrl(me?.avatar_url || googleAvatar);

    if (devPreview && !user) {
      setBio("");
      return;
    }

    authApi
      .getMyProfile()
      .then((profile) => {
        if (cancelled) return;
        setBio(profile.bio ?? "");
        setAvatarUrl(profile.avatar_url || googleAvatar);
        setName(profile.display_name || googleName);
        setProfileNeedsOnboarding(!profile.display_name?.trim());
      })
      .catch(() => {
        /* El formulario puede funcionar con los metadatos de Supabase. */
        if (!cancelled) setProfileNeedsOnboarding(false);
      });

    return () => {
      cancelled = true;
    };
  }, [devPreview, googleAvatar, googleName, me?.avatar_url, user]);

  const save = async () => {
    const displayName = name.trim();
    if (displayName.length < 2) {
      toast.error("El nombre visible debe tener al menos 2 caracteres");
      return;
    }

    setSaving(true);
    try {
      if (devPreview && !user) {
        localStorage.setItem(
          "bct_welcome_preview",
          JSON.stringify({ display_name: displayName, avatar_url: avatarUrl || null }),
        );
        setDismissed(true);
        toast.success("Prueba local completada");
        return;
      }

      await authApi.updateMyProfile({
        display_name: displayName.slice(0, 50),
        bio,
        avatar_url: avatarUrl || null,
      });
      await refreshMe();
      setDismissed(true);
      toast.success("Perfil preparado");
    } catch {
      toast.error("No se pudo guardar tu perfil");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen && !saving) setDismissed(true);
      }}
    >
      <DialogContent className="max-w-md border-cyan-glow/60 bg-surface-800 p-0 text-foreground shadow-[0_0_28px_rgba(34,211,238,0.18)] sm:rounded-none">
        <div className="border-b border-surface-700 px-6 py-5 text-center">
          <div className="mx-auto mb-4 flex size-16 items-center justify-center overflow-hidden rounded-full border border-cyan-glow/50 bg-surface-900">
            {avatarUrl ? (
              <img
                src={avatarUrl}
                alt=""
                className="size-full object-cover"
                referrerPolicy="no-referrer"
                onError={() => setAvatarUrl("")}
              />
            ) : (
              <UserIcon className="size-7 text-cyan-glow" />
            )}
          </div>
          <DialogHeader className="text-center sm:text-center">
            <DialogTitle className="text-2xl font-bold tracking-tight">
              Bienvenido a BuenChollo Tech
            </DialogTitle>
            <DialogDescription className="text-sm leading-relaxed text-muted-foreground">
              Hemos creado tu cuenta con Google. Elige cómo quieres aparecer en la comunidad.
            </DialogDescription>
          </DialogHeader>
        </div>

        <div className="space-y-5 px-6 py-5">
          <div className="border border-cyan-glow/30 bg-cyan-glow/10 px-3 py-2 text-center font-mono text-[11px] text-cyan-glow">
            Este nombre será visible en tus comentarios y actividad pública.
          </div>

          <div>
            <label
              htmlFor="welcome-display-name"
              className="mb-2 block font-mono text-xs font-bold uppercase text-cyan-glow"
            >
              Nombre visible
            </label>
            <input
              id="welcome-display-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={50}
              className="w-full border border-surface-600 bg-surface-900 px-3 py-3 text-base text-foreground outline-none transition-colors focus:border-cyan-glow"
              autoFocus
            />
          </div>

          <div className="grid gap-3 sm:grid-cols-[1fr_1.25fr]">
            <button
              type="button"
              onClick={() => setName(googleName)}
              disabled={!googleName || saving}
              className="border border-surface-600 px-4 py-3 font-mono text-xs font-bold text-muted-foreground transition-colors hover:border-cyan-glow hover:text-cyan-glow disabled:cursor-not-allowed disabled:opacity-50"
            >
              USAR NOMBRE DE GOOGLE
            </button>
            <button
              type="button"
              onClick={save}
              disabled={saving}
              className="bg-cyan-glow px-4 py-3 font-mono text-xs font-bold text-surface-900 transition-colors hover:bg-foreground disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? "GUARDANDO..." : "CONFIRMAR NOMBRE"}
            </button>
          </div>

          <p className="text-center text-xs text-muted-foreground">
            Siempre podrás cambiarlo más tarde desde tu perfil.
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
