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

    window.addEventListener("scroll", updateFooterAtPageEnd, { passive: true });
    return () => window.removeEventListener("scroll", updateFooterAtPageEnd);
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
