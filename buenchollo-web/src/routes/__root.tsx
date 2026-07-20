import { Outlet, Link, createRootRoute, HeadContent, Scripts } from "@tanstack/react-router";
import { useEffect } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/hooks/useAuth";
import { initErrorTracking } from "@/lib/logger";
import { Toaster } from "@/components/ui/sonner";
import { WelcomeProfileDialog } from "@/features/auth/components/WelcomeProfileDialog";
import { queryClient } from "@/lib/query-client";

import { SITE_URL } from "@/lib/site";

import appCss from "../styles.css?url";

function NotFoundComponent() {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <div className="font-mono text-cyan-glow text-sm mb-4">&gt; ERROR_404</div>
        <h1 className="text-7xl font-bold text-foreground tracking-tighter">404</h1>
        <h2 className="mt-4 text-xl font-semibold">Página no encontrada</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          La ruta que buscas no existe o ha sido movida.
        </p>
        <div className="mt-6">
          <Link
            to="/"
            className="inline-flex items-center justify-center bg-cyan-glow text-surface-900 px-6 py-3 font-mono text-xs font-bold hover:bg-foreground transition-colors"
          >
            VOLVER AL INICIO
          </Link>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "BuenChollo Tech — Las mejores ofertas de tecnología" },
      {
        name: "description",
        content:
          "Portal de ofertas y chollos de tecnología y electrónica. Descuentos curados, alertas personalizadas y comunidad.",
      },
      { name: "author", content: "BuenChollo Tech" },
      { name: "theme-color", content: "#0b1120" },
      { property: "og:title", content: "BuenChollo Tech — Las mejores ofertas de tecnología" },
      {
        property: "og:description",
        content:
          "Portal de ofertas y chollos de tecnología y electrónica. Descuentos curados, alertas personalizadas y comunidad.",
      },
      { property: "og:type", content: "website" },
      { property: "og:site_name", content: "BuenChollo Tech" },
      { property: "og:locale", content: "es_ES" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:title", content: "BuenChollo Tech — Las mejores ofertas de tecnología" },
      {
        name: "twitter:description",
        content:
          "Portal de ofertas y chollos de tecnología y electrónica. Descuentos curados, alertas personalizadas y comunidad.",
      },
      {
        property: "og:image",
        content: `${SITE_URL}/og-image.png`,
      },
      {
        name: "twitter:image",
        content: `${SITE_URL}/og-image.png`,
      },
    ],
    links: [
      { rel: "stylesheet", href: appCss },
      { rel: "icon", type: "image/png", href: "/favicon.png?v=2" },
      { rel: "shortcut icon", type: "image/png", href: "/favicon.png?v=2" },
      { rel: "apple-touch-icon", href: "/favicon.png?v=2" },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "" },
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap",
      },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
});

function RootShell({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="dark">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  // Error tracking del navegador (TD-14). Inerte si VITE_SENTRY_DSN está
  // vacío; el SDK se carga en un chunk aparte solo cuando hay DSN.
  useEffect(() => {
    void initErrorTracking();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Outlet />
        <WelcomeProfileDialog />
        <Toaster />
      </AuthProvider>
    </QueryClientProvider>
  );
}
