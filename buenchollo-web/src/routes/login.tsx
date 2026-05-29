import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { lovable } from "@/integrations/lovable";
import { useAuth } from "@/hooks/useAuth";
import { Logo } from "@/components/Logo";
import { toast } from "sonner";
import { z } from "zod";

export const Route = createFileRoute("/login")({
  component: LoginPage,
  head: () => ({
    meta: [
      { title: "Acceder · BuencholloTech" },
      {
        name: "description",
        content:
          "Accede a tu cuenta de BuencholloTech para gestionar alertas, favoritos y notificaciones.",
      },
      { property: "og:title", content: "Acceder · BuencholloTech" },
      {
        property: "og:description",
        content:
          "Accede a tu cuenta de BuencholloTech para gestionar alertas, favoritos y notificaciones.",
      },
      { property: "og:url", content: "https://buenchollotech.lovable.app/login" },
      { name: "robots", content: "noindex, nofollow" },
    ],
    links: [{ rel: "canonical", href: "https://buenchollotech.lovable.app/login" }],
  }),
});

const schema = z.object({
  email: z.string().trim().email({ message: "Email inválido" }).max(255),
  password: z.string().min(6, { message: "Mínimo 6 caracteres" }).max(72),
});

function LoginPage() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  if (user) {
    nav({ to: "/" });
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
      toast.error("Credenciales incorrectas");
      return;
    }
    toast.success("Sesión iniciada");
    nav({ to: "/" });
  };

  const onGoogle = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: window.location.origin,
      },
    });
    if (error) {
      toast.error("No se pudo iniciar sesión con Google");
      return;
    }
  };

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
              <label className="block text-xs font-mono uppercase text-muted-foreground mb-1">
                Contraseña
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full bg-surface-900 border border-surface-700 px-3 py-2.5 font-mono text-sm outline-none focus:border-cyan-glow text-foreground"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-cyan-glow text-surface-900 font-mono text-xs font-bold py-3 hover:bg-foreground transition-colors disabled:opacity-50"
            >
              {loading ? "[ CONECTANDO... ]" : "[ INICIAR SESIÓN ]"}
            </button>
          </form>

          <p className="text-center text-sm text-muted-foreground mt-6">
            ¿No tienes cuenta?{" "}
            <Link to="/registro" className="text-cyan-glow hover:underline">
              Regístrate
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
