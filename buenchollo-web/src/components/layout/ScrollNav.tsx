import { useEffect, useState } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";

const SHOW_AFTER_PX = 400;

export function ScrollNav() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > SHOW_AFTER_PX);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  if (!visible) return null;

  const scrollToTop = () => window.scrollTo({ top: 0, behavior: "smooth" });
  const scrollToFooter = () =>
    document.querySelector("footer")?.scrollIntoView({ behavior: "smooth", block: "start" });

  return (
    <div className="fixed inset-x-0 bottom-0 z-30 border-t border-surface-700 bg-surface-800/95 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-2.5 flex items-center justify-between gap-3">
        <button
          onClick={scrollToTop}
          className="inline-flex items-center gap-1.5 font-mono text-xs text-muted-foreground hover:text-cyan-glow transition-colors"
        >
          <ChevronUp className="size-4" />
          Ir arriba
        </button>
        <button
          onClick={scrollToFooter}
          className="inline-flex items-center gap-1.5 font-mono text-xs text-muted-foreground hover:text-cyan-glow transition-colors"
        >
          Mostrar pie de página
          <ChevronDown className="size-4" />
        </button>
      </div>
    </div>
  );
}
