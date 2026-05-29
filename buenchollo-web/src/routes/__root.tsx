import { Outlet, Link, createRootRoute, HeadContent, Scripts } from "@tanstack/react-router";
import { AuthProvider } from "@/hooks/useAuth";
import { Toaster } from "@/components/ui/sonner";

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
            [ VOLVER AL INICIO ]
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
      { title: "BuencholloTech — Las mejores ofertas de tecnología" },
      {
        name: "description",
        content:
          "Portal de ofertas y chollos de tecnología y electrónica. Descuentos curados, alertas personalizadas y comunidad.",
      },
      { name: "author", content: "BuencholloTech" },
      { property: "og:title", content: "BuencholloTech — Las mejores ofertas de tecnología" },
      {
        property: "og:description",
        content:
          "Portal de ofertas y chollos de tecnología y electrónica. Descuentos curados, alertas personalizadas y comunidad.",
      },
      { property: "og:type", content: "website" },
      { property: "og:site_name", content: "BuencholloTech" },
      { property: "og:locale", content: "es_ES" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:title", content: "BuencholloTech — Las mejores ofertas de tecnología" },
      {
        name: "twitter:description",
        content:
          "Portal de ofertas y chollos de tecnología y electrónica. Descuentos curados, alertas personalizadas y comunidad.",
      },
      {
        property: "og:image",
        content:
          "https://pub-bb2e103a32db4e198524a2e9ed8f35b4.r2.dev/2d10f0b6-2af5-434a-8618-dbc51e27c961/id-preview-5636a208--6598b564-42fc-4036-9f9c-29d936b259e5.lovable.app-1776711372677.png",
      },
      {
        name: "twitter:image",
        content:
          "https://pub-bb2e103a32db4e198524a2e9ed8f35b4.r2.dev/2d10f0b6-2af5-434a-8618-dbc51e27c961/id-preview-5636a208--6598b564-42fc-4036-9f9c-29d936b259e5.lovable.app-1776711372677.png",
      },
    ],
    scripts: [
      {
        type: "application/ld+json",
        children: JSON.stringify({
          "@context": "https://schema.org",
          "@graph": [
            {
              "@type": "Organization",
              "@id": "https://buenchollotech.lovable.app/#org",
              name: "BuencholloTech",
              url: "https://buenchollotech.lovable.app/",
              logo: "https://buenchollotech.lovable.app/favicon.png",
              sameAs: ["https://t.me/buenchollotech"],
            },
            {
              "@type": "WebSite",
              "@id": "https://buenchollotech.lovable.app/#site",
              url: "https://buenchollotech.lovable.app/",
              name: "BuencholloTech",
              publisher: { "@id": "https://buenchollotech.lovable.app/#org" },
              inLanguage: "es-ES",
              potentialAction: {
                "@type": "SearchAction",
                target: "https://buenchollotech.lovable.app/explorar?q={search_term_string}",
                "query-input": "required name=search_term_string",
              },
            },
          ],
        }),
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
  return (
    <AuthProvider>
      <Outlet />
      <Toaster />
    </AuthProvider>
  );
}
