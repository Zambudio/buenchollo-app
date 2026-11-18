import { Outlet, Link, createRootRoute, HeadContent, Scripts } from "@tanstack/react-router";
import { useEffect } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/hooks/useAuth";
import { ThemeProvider, THEME_INIT_SCRIPT } from "@/hooks/useTheme";
import { initErrorTracking } from "@/lib/logger";
import { Toaster } from "@/components/ui/sonner";
import { WelcomeProfileDialog } from "@/features/auth/components/WelcomeProfileDialog";
import { queryClient } from "@/lib/query-client";
import { AnalyticsTracker } from "@/features/analytics/components/AnalyticsTracker";

import { SITE_URL } from "@/lib/site";

import appCss from "../styles.css?url";

function NotFoundComponent() {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-background px-4">
      {/* React 19 lleva estas etiquetas al <head>; el servidor responde 404. */}
      <title>Página no encontrada | BuenChollo Tech</title>
      <meta name="robots" content="noindex" />
      <div className="max-w-md text-center">
        <div className="font-mono text-cyan-glow text-sm mb-4">&gt; ERROR_404</div>
        <h1 className="text-7xl font-bold text-foreground tracking-tighter">404</h1>
        <h2 className="mt-4 text-xl font-semibold">Página no encontrada</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          El chollo o la página que buscas no existe o ha sido retirada.
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/"
            className="inline-flex items-center justify-center bg-cyan-glow text-surface-900 px-6 py-3 font-mono text-xs font-bold hover:bg-foreground transition-colors"
          >
            VER CHOLLOS DE HOY
          </Link>
          <Link
            to="/categorias"
            className="inline-flex items-center justify-center border border-surface-700 px-6 py-3 font-mono text-xs font-bold hover:border-cyan-glow transition-colors"
          >
            CATEGORÍAS
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
      { rel: "icon", href: "/favicon.ico", sizes: "any" },
      { rel: "icon", type: "image/png", sizes: "32x32", href: "/favicon-32.png?v=3" },
      { rel: "icon", type: "image/png", sizes: "192x192", href: "/favicon.png?v=3" },
      { rel: "apple-touch-icon", sizes: "180x180", href: "/apple-touch-icon.png?v=3" },
      {
        rel: "alternate",
        type: "application/rss+xml",
        title: "Chollos de BuenChollo Tech",
        href: `${SITE_URL}/rss.xml`,
      },
      {
        rel: "alternate",
        type: "application/rss+xml",
        title: "Blog de BuenChollo Tech",
        href: `${SITE_URL}/blog/rss.xml`,
      },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
});

function RootShell({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="dark" suppressHydrationWarning>
      <head>
        {/* Aplica la preferencia de tema guardada/del sistema antes del primer
            pintado, para evitar un parpadeo de tema oscuro → claro (FOUC). */}
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
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
      <ThemeProvider>
        <AuthProvider>
          <AnalyticsTracker />
          <Outlet />
          <WelcomeProfileDialog />
          <Toaster />
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
