import { ReactNode, useEffect, useState } from "react";
import { Header } from "./Header";
import { CategoryBar } from "./CategoryBar";
import { Footer } from "./Footer";
import { ScrollNav } from "./ScrollNav";
import { CookieBanner } from "./CookieBanner";

export function Layout({ children }: { children: ReactNode }) {
  const [footerVisible, setFooterVisible] = useState(false);

  useEffect(() => {
    if (!footerVisible) return;

    const initialScrollY = window.scrollY;
    let listening = false;
    const frame = window.requestAnimationFrame(() => {
      listening = true;
    });
    const hideFooterOnScroll = () => {
      if (listening && Math.abs(window.scrollY - initialScrollY) > 1) setFooterVisible(false);
    };

    window.addEventListener("scroll", hideFooterOnScroll, { passive: true });
    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("scroll", hideFooterOnScroll);
    };
  }, [footerVisible]);

  return (
    <div className="min-h-dvh flex flex-col bg-background text-foreground">
      <Header />
      <CategoryBar />
      <main className="flex-1">{children}</main>
      {footerVisible ? (
        <div
          className="fixed inset-x-0 bottom-0 z-30 max-h-[calc(100dvh-4rem)] overflow-y-auto bg-surface-800 shadow-[0_-8px_30px_rgba(0,0,0,0.45)]"
          onWheel={() => setFooterVisible(false)}
          onTouchMove={() => setFooterVisible(false)}
        >
          <ScrollNav footerVisible docked onToggleFooter={() => setFooterVisible(false)} />
          <Footer />
        </div>
      ) : (
        <ScrollNav footerVisible={false} onToggleFooter={() => setFooterVisible(true)} />
      )}
      <CookieBanner />
    </div>
  );
}
