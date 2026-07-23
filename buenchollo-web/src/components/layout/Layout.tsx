import { ReactNode, useEffect, useRef, useState } from "react";
import { Header } from "./Header";
import { CategoryBar } from "./CategoryBar";
import { Footer } from "./Footer";
import { ScrollNav } from "./ScrollNav";
import { CookieBanner } from "./CookieBanner";

export function Layout({ children }: { children: ReactNode }) {
  const [footerMode, setFooterMode] = useState<"closed" | "manual" | "auto">("closed");
  const autoFooterStartY = useRef(0);

  useEffect(() => {
    const updateFooterAtPageEnd = () => {
      const pageEnd =
        window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2;
      setFooterMode((current) => {
        if (current === "closed" && pageEnd) {
          autoFooterStartY.current = window.scrollY;
          return "auto";
        }
        if (current === "auto" && window.scrollY < autoFooterStartY.current - 24) return "closed";
        return current;
      });
    };

    // Comprobación inmediata: si la página ya es más corta que la pantalla
    // (p. ej. /blog con pocos artículos), nunca se dispara un evento
    // "scroll" y el footer se quedaría escondido para siempre sin esto.
    updateFooterAtPageEnd();

    // ResizeObserver: revalida cuando cambia la altura del documento (datos
    // cargados de forma async, imágenes, cambio de tamaño de ventana) sin
    // depender de que el usuario haga scroll. No disponible en jsdom (tests).
    const resizeObserver =
      typeof ResizeObserver !== "undefined" ? new ResizeObserver(updateFooterAtPageEnd) : null;
    resizeObserver?.observe(document.documentElement);

    window.addEventListener("scroll", updateFooterAtPageEnd, { passive: true });
    window.addEventListener("resize", updateFooterAtPageEnd);
    return () => {
      resizeObserver?.disconnect();
      window.removeEventListener("scroll", updateFooterAtPageEnd);
      window.removeEventListener("resize", updateFooterAtPageEnd);
    };
  }, []);

  return (
    <div className="min-h-dvh flex flex-col bg-background text-foreground">
      <Header />
      <CategoryBar />
      <main className="flex-1">{children}</main>
      {footerMode === "manual" ? (
        <div
          className="fixed inset-x-0 bottom-0 z-30 max-h-[calc(100dvh-4rem)] overflow-y-auto bg-surface-800 shadow-[0_-8px_30px_rgba(0,0,0,0.45)]"
          onWheel={() => setFooterMode("closed")}
          onTouchMove={() => setFooterMode("closed")}
        >
          <ScrollNav footerVisible docked onToggleFooter={() => setFooterMode("closed")} />
          <Footer />
        </div>
      ) : footerMode === "auto" ? (
        <div className="bg-surface-800">
          <ScrollNav
            footerVisible
            docked
            showFooterToggle={false}
            onToggleFooter={() => setFooterMode("closed")}
          />
          <Footer />
        </div>
      ) : (
        <ScrollNav footerVisible={false} onToggleFooter={() => setFooterMode("manual")} />
      )}
      <CookieBanner />
    </div>
  );
}
