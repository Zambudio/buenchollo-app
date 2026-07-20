import { useEffect, useState } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";

const SHOW_AFTER_PX = 400;

export function ScrollNav({
  footerVisible,
  onToggleFooter,
  docked = false,
  showFooterToggle = true,
}: {
  footerVisible: boolean;
  onToggleFooter: () => void;
  docked?: boolean;
  showFooterToggle?: boolean;
}) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > SHOW_AFTER_PX);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  if (!visible && !footerVisible) return null;

  const scrollToTop = () => window.scrollTo({ top: 0, behavior: "smooth" });

  return (
    <div
      className={`${docked ? "sticky top-0" : "fixed inset-x-0 bottom-0"} z-30 border-t border-cyan-glow/30 bg-surface-800/95 backdrop-blur-md shadow-[0_-4px_20px_rgba(0,0,0,0.3)]`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={scrollToTop}
          className="inline-flex items-center gap-2 font-mono text-sm font-bold uppercase tracking-wide text-foreground px-3 py-2 hover:bg-surface-700 hover:text-cyan-glow transition-colors"
        >
          <ChevronUp className="size-5" />
          Ir arriba
        </button>
        {showFooterToggle && (
          <button
            type="button"
            onClick={onToggleFooter}
            aria-expanded={footerVisible}
            aria-controls="site-footer"
            className="inline-flex items-center gap-2 font-mono text-sm font-bold uppercase tracking-wide text-foreground px-3 py-2 hover:bg-surface-700 hover:text-cyan-glow transition-colors"
          >
            {footerVisible ? "Ocultar pie de página" : "Mostrar pie de página"}
            {footerVisible ? <ChevronUp className="size-5" /> : <ChevronDown className="size-5" />}
          </button>
        )}
      </div>
    </div>
  );
}
