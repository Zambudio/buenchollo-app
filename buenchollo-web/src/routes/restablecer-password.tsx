import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Logo } from "@/components/layout/Logo";
import { PasswordInput } from "@/components/ui/PasswordInput";
import { toast } from "sonner";
import { KeyRound, CheckCircle2, AlertTriangle, ArrowLeft } from "lucide-react";
import { SITE_URL } from "@/lib/site";

export const Route = createFileRoute("/restablecer-password")({
  component: ResetPasswordPage,
  head: () => ({
    meta: [
      { title: "Restablecer contraseña · BuenChollo Tech" },
      {
        name: "description",
        content: "Introduce una nueva contraseña para acceder a tu cuenta de BuenChollo Tech.",
      },
      { property: "og:title", content: "Restablecer contraseña · BuenChollo Tech" },
      { property: "og:url", content: `${SITE_URL}/restablecer-password` },
      { name: "robots", content: "noindex, nofollow" },
    ],
    links: [{ rel: "canonical", href: `${SITE_URL}/restablecer-password` }],
  }),
});

function ResetPasswordPage() {
  const nav = useNavigate();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(true);
  const [hasValidSession, setHasValidSession] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    let mounted = true;

    // Escuchar evento específico de recuperación
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (!mounted) return;
      if (event === "PASSWORD_RECOVERY" || session) {
        setHasValidSession(true);
        setChecking(false);
      }
    });

    // Verificar si ya hay una sesión activa o tokens en el hash/URL
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!mounted) return;
      const hash = typeof window !== "undefined" ? window.location.hash : "";
      const search = typeof window !== "undefined" ? window.location.search : "";
      const isRecoveryFlow =
        Boolean(session) ||
        hash.includes("type=recovery") ||
        hash.includes("access_token") ||
        search.includes("code=");

      setHasValidSession(isRecoveryFlow);
      setChecking(false);
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (password.length < 6) {
      toast.error("La contraseña debe tener al menos 6 caracteres");
      return;
    }

    if (password !== confirmPassword) {
      toast.error("Las contraseñas no coinciden");
      return;
    }

    setLoading(true);
    const { error } = await supabase.auth.updateUser({ password });
    setLoading(false);

    if (error) {
      toast.error("No se pudo actualizar la contraseña: " + error.message);
      return;
    }

    setSuccess(true);
    toast.success("Contraseña actualizada con éxito");
    setTimeout(() => {
      nav({ to: "/login" });
    }, 2500);
  };

  return (
    <div className="min-h-dvh flex items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-md">
        <Link to="/" className="flex justify-center mb-8">
          <Logo />
        </Link>

        <div className="bg-surface-800 border border-surface-700 p-6 sm:p-8">
          {checking ? (
            <div className="py-12 text-center font-mono text-xs text-muted-foreground">
              Verificando enlace de seguridad...
            </div>
          ) : success ? (
            <div className="text-center py-4 space-y-4">
              <div className="mx-auto flex size-14 items-center justify-center rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                <CheckCircle2 className="size-7" />
              </div>
              <div className="font-mono text-emerald-400 text-xs">&gt; CONTRASEÑA_RESTABLECIDA</div>
              <h1 className="text-2xl font-bold">¡Nueva contraseña guardada!</h1>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Tu clave ha sido actualizada correctamente. Te redirigimos al inicio de sesión en unos
                instantes...
              </p>
              <Link
                to="/login"
                className="block w-full bg-cyan-glow text-surface-900 font-mono text-xs font-bold py-3 hover:bg-foreground transition-colors text-center"
              >
                IR AHORA A INICIAR SESIÓN
              </Link>
            </div>
          ) : !hasValidSession ? (
            <div className="text-center py-4 space-y-4">
              <div className="mx-auto flex size-14 items-center justify-center rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400">
                <AlertTriangle className="size-7" />
              </div>
              <div className="font-mono text-amber-400 text-xs">&gt; ENLACE_NO_VALIDO</div>
              <h1 className="text-2xl font-bold">Enlace caducado o no válido</h1>
              <p className="text-sm text-muted-foreground leading-relaxed">
                El enlace de recuperación ha caducado (duran 1 hora) o ya ha sido utilizado.
                Por favor, solicita uno nuevo desde la pantalla de acceso.
              </p>
              <Link
                to="/login"
                className="block w-full bg-cyan-glow text-surface-900 font-mono text-xs font-bold py-3 hover:bg-foreground transition-colors text-center"
              >
                SOLICITAR NUEVO ENLACE
              </Link>
            </div>
          ) : (
            <>
              <div className="font-mono text-cyan-glow text-xs mb-2">&gt; RESTABLECER_PASSWORD</div>
              <h1 className="text-2xl font-bold mb-1">Crea tu nueva contraseña</h1>
              <p className="text-sm text-muted-foreground mb-6">
                Elige una contraseña segura de al menos 6 caracteres para acceder a tu cuenta.
              </p>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-mono uppercase text-muted-foreground mb-1">
                    Nueva contraseña
                  </label>
                  <PasswordInput
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={6}
                    placeholder="Mínimo 6 caracteres"
                    className="bg-surface-900 border border-surface-700 px-3 py-2.5 font-mono text-sm outline-none focus:border-cyan-glow text-foreground"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono uppercase text-muted-foreground mb-1">
                    Repite la nueva contraseña
                  </label>
                  <PasswordInput
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    minLength={6}
                    placeholder="Repite tu clave"
                    className="bg-surface-900 border border-surface-700 px-3 py-2.5 font-mono text-sm outline-none focus:border-cyan-glow text-foreground"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-cyan-glow text-surface-900 font-mono text-xs font-bold py-3 hover:bg-foreground transition-colors disabled:opacity-50"
                >
                  {loading ? "GUARDANDO..." : "GUARDAR NUEVA CONTRASEÑA"}
                </button>
              </form>

              <div className="mt-6 text-center">
                <Link
                  to="/login"
                  className="inline-flex items-center gap-1.5 text-xs font-mono text-muted-foreground hover:text-cyan-glow transition-colors"
                >
                  <ArrowLeft className="size-3.5" />
                  VOLVER A INICIAR SESIÓN
                </Link>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
