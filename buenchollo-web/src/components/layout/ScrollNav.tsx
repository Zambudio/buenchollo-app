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

  // Persigue el final real del documento: el scroll infinito de la home puede
  // seguir cargando tarjetas mientras se anima el scroll, así que el "fondo"
  // se mueve. En vez de apuntar una sola vez, recalculamos el objetivo en
  // cada intento y paramos cuando el footer llega arriba o cuando el scroll
  // deja de avanzar entre dos comprobaciones (ya no hay más contenido nuevo).
  const scrollToFooter = () => {
    const maxAttempts = 10;
    let attempts = 0;
    let lastY = -1;

    const step = () => {
      const footer = document.querySelector("footer");
      if (!footer) return;
      const targetY = document.documentElement.scrollHeight - window.innerHeight;
      window.scrollTo({ top: targetY, behavior: "smooth" });
      attempts += 1;

      setTimeout(() => {
        const currentY = window.scrollY;
        const reachedTop = footer.getBoundingClientRect().top <= 4;
        const converged = currentY === lastY;
        lastY = currentY;
        if (!reachedTop && !converged && attempts < maxAttempts) step();
      }, 600);
    };

    step();
  };

  return (
    <div className="fixed inset-x-0 bottom-0 z-30 border-t border-cyan-glow/30 bg-surface-800/95 backdrop-blur-md shadow-[0_-4px_20px_rgba(0,0,0,0.3)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={scrollToTop}
          className="inline-flex items-center gap-2 font-mono text-sm font-bold uppercase tracking-wide text-foreground px-3 py-2 hover:bg-surface-700 hover:text-cyan-glow transition-colors"
        >
          <ChevronUp className="size-5" />
          Ir arriba
        </button>
        <button
          type="button"
          onClick={scrollToFooter}
          className="inline-flex items-center gap-2 font-mono text-sm font-bold uppercase tracking-wide text-foreground px-3 py-2 hover:bg-surface-700 hover:text-cyan-glow transition-colors"
        >
          Mostrar pie de página
          <ChevronDown className="size-5" />
        </button>
      </div>
    </div>
  );
}
