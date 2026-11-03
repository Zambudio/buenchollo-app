import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { signInWithGoogle } from "@/lib/auth";
import { useAuth } from "@/hooks/useAuth";
import { Logo } from "@/components/layout/Logo";
import { PasswordInput } from "@/components/ui/PasswordInput";
import { toast } from "sonner";
import { z } from "zod";
import { SITE_URL } from "@/lib/site";
import { authApi } from "@/services/api/auth";
import { translateAuthError } from "@/lib/errors";
import { Mail, ArrowLeft } from "lucide-react";
import { loginSearch, safeRedirect } from "@/lib/safe-redirect";

export const Route = createFileRoute("/login")({
  component: LoginPage,
  validateSearch: (s: Record<string, unknown>): { redirect?: string } => ({
    redirect: typeof s.redirect === "string" ? s.redirect : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Acceder · BuenChollo Tech" },
      {
        name: "description",
        content:
          "Accede a tu cuenta de BuenChollo Tech para gestionar alertas, favoritos y notificaciones.",
      },
      { property: "og:title", content: "Acceder · BuenChollo Tech" },
      {
        property: "og:description",
        content:
          "Accede a tu cuenta de BuenChollo Tech para gestionar alertas, favoritos y notificaciones.",
      },
      { property: "og:url", content: `${SITE_URL}/login` },
      { name: "robots", content: "noindex, nofollow" },
    ],
    links: [{ rel: "canonical", href: `${SITE_URL}/login` }],
  }),
});

const schema = z.object({
  email: z.string().trim().email({ message: "Email inválido" }).max(255),
  password: z.string().min(6, { message: "Mínimo 6 caracteres" }).max(72),
});

function LoginPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const { redirect } = Route.useSearch();
  const target = safeRedirect(redirect);
  // El submit y el efecto de "ya hay sesión" pueden dispararse ambos: se
  // navega una sola vez y con replace para no dejar /login en el historial.
  const navigated = useRef(false);
  const goAfterLogin = useCallback(() => {
    if (navigated.current) return;
    navigated.current = true;
    router.history.replace(target);
  }, [router, target]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  // Estados de recuperación de contraseña
  const [showRecovery, setShowRecovery] = useState(false);
  const [recoveryEmail, setRecoveryEmail] = useState("");
  const [recoveryLoading, setRecoveryLoading] = useState(false);
  const [recoverySent, setRecoverySent] = useState(false);

  // Redirección segura fuera del render cuando hay sesión activa
  useEffect(() => {
    if (authLoading) return;
    if (user) {
      if (typeof window !== "undefined" && window.location.hash) {
        window.history.replaceState(null, "", window.location.pathname + window.location.search);
      }
      toast.success("¡Bienvenido a BuenChollo Tech!", { id: "welcome-toast" });
      const name = user.user_metadata?.display_name || user.email?.split("@")[0] || "Chollero";
      void authApi.sendWelcomeEmail(name).catch(() => {});
      goAfterLogin();
    }
  }, [authLoading, user, goAfterLogin]);

  // Mensaje cuando la cuenta ha sido confirmada vía callback de Supabase
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("confirmed") === "1" || params.get("confirmed") === "true") {
      toast.success("¡Correo confirmado correctamente! Ya puedes iniciar sesión.", {
        duration: 6000,
        id: "auth-confirmed",
      });
    }
  }, []);

  // Manejo de enlaces expirados o ya consumidos si no hay sesión
  useEffect(() => {
    if (typeof window === "undefined" || authLoading) return;
    const hash = window.location.hash;
    if (!user && (hash.includes("otp_expired") || hash.includes("access_denied"))) {
      toast.error(
        "El enlace de confirmación ha caducado o ya ha sido utilizado. Si ya confirmaste tu cuenta, inicia sesión directamente.",
        {
          duration: 7000,
          id: "auth-otp-expired",
        },
      );
      window.history.replaceState(null, "", window.location.pathname + window.location.search);
    }
  }, [authLoading, user]);

  if (user) {
    return null;
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = schema.safeParse({ email, password });
    if (!parsed.success) {
      toast.error(parsed.error.issues[0]?.message ?? "Datos inválidos");
      return;
    }
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword(parsed.data);
    setLoading(false);
    if (error) {
      toast.error(translateAuthError(error.message, "Credenciales incorrectas"));
      return;
    }
    toast.success("Sesión iniciada");
    goAfterLogin();
  };

  const onResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanEmail = recoveryEmail.trim();
    if (!cleanEmail || !cleanEmail.includes("@")) {
      toast.error("Introduce un correo válido");
      return;
    }
    setRecoveryLoading(true);
    const { error } = await supabase.auth.resetPasswordForEmail(cleanEmail, {
      redirectTo: `${window.location.origin}/restablecer-password`,
    });
    setRecoveryLoading(false);
    if (error) {
      toast.error(translateAuthError(error.message));
      return;
    }
    setRecoverySent(true);
    toast.success("Enlace de recuperación enviado");
  };

  const onGoogle = async () => {
    const { error } = await signInWithGoogle(target);
    if (error) {
      toast.error(translateAuthError(error.message, "No se pudo iniciar sesión con Google"));
      return;
    }
  };

  if (showRecovery) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-background px-4 py-12">
        <div className="w-full max-w-md">
          <Link to="/" className="flex justify-center mb-8">
            <Logo />
          </Link>
          <div className="bg-surface-800 border border-surface-700 p-6 sm:p-8">
            <button
              onClick={() => {
                setShowRecovery(false);
                setRecoverySent(false);
              }}
              className="inline-flex items-center gap-1.5 text-xs font-mono text-muted-foreground hover:text-cyan-glow mb-4 transition-colors"
            >
              <ArrowLeft className="size-3.5" />
              VOLVER AL LOGIN
            </button>

            <div className="font-mono text-cyan-glow text-xs mb-2">&gt; AUTH_PASSWORD_RESET</div>
            <h1 className="text-2xl font-bold mb-1">Recuperar contraseña</h1>
            <p className="text-sm text-muted-foreground mb-6">
              Te enviaremos un correo con un enlace seguro para crear una nueva clave.
            </p>

            {recoverySent ? (
              <div className="text-center py-4 space-y-4">
                <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-cyan-glow/10 border border-cyan-glow/30 text-cyan-glow">
                  <Mail className="size-6" />
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Si existe una cuenta asociada a{" "}
                  <strong className="text-foreground">{recoveryEmail}</strong>, recibirás un correo
                  con las instrucciones en tu bandeja de entrada en unos instantes.
                </p>
                <button
                  onClick={() => {
                    setShowRecovery(false);
                    setRecoverySent(false);
                  }}
                  className="w-full bg-cyan-glow text-surface-900 font-mono text-xs font-bold py-3 hover:bg-foreground transition-colors"
                >
                  VOLVER A INICIAR SESIÓN
                </button>
              </div>
            ) : (
              <form onSubmit={onResetPassword} className="space-y-4">
                <div>
                  <label className="block text-xs font-mono uppercase text-muted-foreground mb-1">
                    Tu correo electrónico
                  </label>
                  <input
                    type="email"
                    value={recoveryEmail}
                    onChange={(e) => setRecoveryEmail(e.target.value)}
                    required
                    placeholder="ejemplo@correo.com"
                    className="w-full bg-surface-900 border border-surface-700 px-3 py-2.5 font-mono text-sm outline-none focus:border-cyan-glow text-foreground"
                  />
                </div>
                <button
                  type="submit"
                  disabled={recoveryLoading}
                  className="w-full bg-cyan-glow text-surface-900 font-mono text-xs font-bold py-3 hover:bg-foreground transition-colors disabled:opacity-50"
                >
                  {recoveryLoading ? "ENVIANDO..." : "ENVIAR ENLACE DE RECUPERACIÓN"}
                </button>
              </form>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-dvh flex items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-md">
        <Link to="/" className="flex justify-center mb-8">
          <Logo />
        </Link>
        <div className="bg-surface-800 border border-surface-700 p-6 sm:p-8">
          <div className="font-mono text-cyan-glow text-xs mb-2">&gt; AUTH_LOGIN</div>
          <h1 className="text-2xl font-bold mb-1">Acceder a tu cuenta</h1>
          <p className="text-sm text-muted-foreground mb-6">
            Bienvenido de vuelta. Vamos a interceptar más chollos.
          </p>

          <button
            onClick={onGoogle}
            className="w-full mb-4 border border-surface-700 bg-surface-900 hover:border-cyan-glow text-foreground font-mono text-xs font-bold py-3 transition-colors flex items-center justify-center gap-2"
          >
            <svg className="size-4" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            CONTINUAR CON GOOGLE
          </button>

          <p className="text-xs text-muted-foreground leading-relaxed mb-4">
            Al continuar, aceptas los{" "}
            <Link to="/terminos-y-condiciones" className="text-cyan-glow hover:underline">
              Términos y condiciones
            </Link>{" "}
            y confirmas que has leído la{" "}
            <Link to="/politica-de-privacidad" className="text-cyan-glow hover:underline">
              Política de privacidad
            </Link>
            .
          </p>

          <div className="flex items-center gap-3 my-4 text-xs font-mono text-muted-foreground">
            <div className="flex-1 h-px bg-surface-700" /> O{" "}
            <div className="flex-1 h-px bg-surface-700" />
          </div>

          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-mono uppercase text-muted-foreground mb-1">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full bg-surface-900 border border-surface-700 px-3 py-2.5 font-mono text-sm outline-none focus:border-cyan-glow text-foreground"
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-mono uppercase text-muted-foreground">
                  Contraseña
                </label>
                <button
                  type="button"
                  onClick={() => setShowRecovery(true)}
                  className="text-xs text-cyan-glow hover:underline font-mono"
                >
                  ¿Olvidaste tu contraseña?
                </button>
              </div>
              <PasswordInput
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="bg-surface-900 border border-surface-700 px-3 py-2.5 font-mono text-sm outline-none focus:border-cyan-glow text-foreground"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-cyan-glow text-surface-900 font-mono text-xs font-bold py-3 hover:bg-foreground transition-colors disabled:opacity-50"
            >
              {loading ? "CONECTANDO..." : "INICIAR SESIÓN"}
            </button>
          </form>

          <p className="text-center text-sm text-muted-foreground mt-6">
            ¿No tienes cuenta?{" "}
            <Link
              to="/registro"
              search={loginSearch(redirect)}
              className="text-cyan-glow hover:underline"
            >
              Regístrate
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
