import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
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
import { Mail, RefreshCw } from "lucide-react";
import { loginSearch, safeRedirect } from "@/lib/safe-redirect";

export const Route = createFileRoute("/registro")({
  component: RegisterPage,
  validateSearch: (s: Record<string, unknown>): { redirect?: string } => ({
    redirect: typeof s.redirect === "string" ? s.redirect : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Crear cuenta · BuenChollo Tech" },
      {
        name: "description",
        content:
          "Crea una cuenta gratuita en BuenChollo Tech para crear alertas y guardar tus chollos favoritos.",
      },
      { property: "og:title", content: "Crear cuenta · BuenChollo Tech" },
      {
        property: "og:description",
        content:
          "Crea una cuenta gratuita en BuenChollo Tech para crear alertas y guardar tus chollos favoritos.",
      },
      { property: "og:url", content: `${SITE_URL}/registro` },
    ],
    links: [{ rel: "canonical", href: `${SITE_URL}/registro` }],
  }),
});

const schema = z.object({
  displayName: z.string().trim().min(2, { message: "Nombre demasiado corto" }).max(50),
  email: z.string().trim().email({ message: "Email inválido" }).max(255),
  password: z.string().min(6, { message: "Contraseña: mínimo 6 caracteres" }).max(72),
});

function RegisterPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const { redirect } = Route.useSearch();
  const target = safeRedirect(redirect);
  const goAfterRegister = useCallback(() => router.history.push(target), [router, target]);
  const confirmUrl = `${typeof window === "undefined" ? "" : window.location.origin}/login?confirmed=1${
    target === "/" ? "" : `&redirect=${encodeURIComponent(target)}`
  }`;
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [needsConfirmation, setNeedsConfirmation] = useState(false);
  const [confirmedEmail, setConfirmedEmail] = useState("");

  useEffect(() => {
    if (authLoading) return;
    if (user) {
      goAfterRegister();
    }
  }, [authLoading, user, goAfterRegister]);

  if (user) {
    return null;
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = schema.safeParse({ displayName, email, password });
    if (!parsed.success) {
      toast.error(parsed.error.issues[0]?.message ?? "Datos inválidos");
      return;
    }
    setLoading(true);
    const { data, error } = await supabase.auth.signUp({
      email: parsed.data.email,
      password: parsed.data.password,
      options: {
        emailRedirectTo: confirmUrl,
        data: { display_name: parsed.data.displayName },
      },
    });
    setLoading(false);
    if (error) {
      toast.error(translateAuthError(error.message));
      return;
    }

    if (data?.user && !data.session) {
      setConfirmedEmail(parsed.data.email);
      setNeedsConfirmation(true);
      return;
    }

    toast.success("Cuenta creada. Bienvenido a BuenChollo Tech.");
    void authApi.sendWelcomeEmail(parsed.data.displayName).catch(() => {});
    goAfterRegister();
  };

  const handleResend = async () => {
    if (!confirmedEmail) return;
    setResending(true);
    const { error } = await supabase.auth.resend({
      type: "signup",
      email: confirmedEmail,
      options: {
        emailRedirectTo: confirmUrl,
      },
    });
    setResending(false);
    if (error) {
      toast.error(translateAuthError(error.message));
    } else {
      toast.success("Correo de confirmación reenviado");
    }
  };

  const onGoogle = async () => {
    const { error } = await signInWithGoogle(target);
    if (error) {
      toast.error(translateAuthError(error.message, "No se pudo registrar con Google"));
      return;
    }
  };

  if (needsConfirmation) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-background px-4 py-12">
        <div className="w-full max-w-md">
          <Link to="/" className="flex justify-center mb-8">
            <Logo />
          </Link>
          <div className="bg-surface-800 border border-surface-700 p-6 sm:p-8 text-center">
            <div className="mx-auto mb-4 flex size-14 items-center justify-center rounded-full bg-cyan-glow/10 border border-cyan-glow/30 text-cyan-glow">
              <Mail className="size-7" />
            </div>
            <div className="font-mono text-cyan-glow text-xs mb-2">&gt; CONFIRMA_TU_CORREO</div>
            <h1 className="text-2xl font-bold mb-2">¡Revisa tu bandeja de entrada!</h1>
            <p className="text-sm text-muted-foreground leading-relaxed mb-6">
              Hemos enviado un enlace de confirmación a{" "}
              <strong className="text-foreground">{confirmedEmail}</strong>. Pulsa en el botón del
              correo para verificar tu cuenta y empezar a interceptar chollos.
            </p>

            <div className="space-y-3">
              <button
                onClick={handleResend}
                disabled={resending}
                className="w-full flex items-center justify-center gap-2 border border-surface-600 bg-surface-900 hover:border-cyan-glow text-foreground font-mono text-xs font-bold py-3 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`size-3.5 ${resending ? "animate-spin" : ""}`} />
                {resending ? "REENVIANDO..." : "REENVIAR CORREO DE CONFIRMACIÓN"}
              </button>

              <Link
                to="/login"
                search={loginSearch(redirect)}
                className="block w-full bg-cyan-glow text-surface-900 font-mono text-xs font-bold py-3 hover:bg-foreground transition-colors text-center"
              >
                IR A INICIAR SESIÓN
              </Link>
            </div>

            <p className="text-xs text-muted-foreground mt-6">
              ¿No lo ves en tu bandeja principal? Recuerda revisar tu carpeta de correo no deseado o
              spam.
            </p>
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
          <div className="font-mono text-cyan-glow text-xs mb-2">&gt; AUTH_REGISTER</div>
          <h1 className="text-2xl font-bold mb-1">Crear cuenta</h1>
          <p className="text-sm text-muted-foreground mb-6">
            Guarda favoritos, crea alertas y nunca pierdas un chollo.
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
            REGISTRARSE CON GOOGLE
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
                Nombre
              </label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
                className="w-full bg-surface-900 border border-surface-700 px-3 py-2.5 font-mono text-sm outline-none focus:border-cyan-glow text-foreground"
              />
            </div>
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
              <label className="block text-xs font-mono uppercase text-muted-foreground mb-1">
                Contraseña
              </label>
              <PasswordInput
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                className="bg-surface-900 border border-surface-700 px-3 py-2.5 font-mono text-sm outline-none focus:border-cyan-glow text-foreground"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-cyan-glow text-surface-900 font-mono text-xs font-bold py-3 hover:bg-foreground transition-colors disabled:opacity-50"
            >
              {loading ? "CREANDO..." : "CREAR CUENTA"}
            </button>
          </form>

          <p className="text-center text-sm text-muted-foreground mt-6">
            ¿Ya tienes cuenta?{" "}
            <Link
              to="/login"
              search={loginSearch(redirect)}
              className="text-cyan-glow hover:underline"
            >
              Acceder
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
