import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { Cookie } from "lucide-react";

const STORAGE_KEY = "cookie-consent-ack";

export function CookieBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setVisible(window.localStorage.getItem(STORAGE_KEY) !== "1");
  }, []);

  const dismiss = () => {
    window.localStorage.setItem(STORAGE_KEY, "1");
    setVisible(false);
  };

  return (
    <div
      className={`fixed left-4 bottom-4 z-50 w-[calc(100%-2rem)] max-w-sm transform transition-all duration-300 ease-in-out ${
        visible ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0 pointer-events-none"
      }`}
      role="region"
      aria-label="Aviso de cookies"
    >
      <div className="rounded-lg border border-cyan-glow/30 bg-surface-800/95 backdrop-blur-md shadow-2xl p-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="inline-flex items-center justify-center size-8 rounded border border-cyan-glow/40 bg-surface-900 text-cyan-glow shrink-0">
            <Cookie className="size-4" />
          </span>
          <h2 className="font-mono text-xs font-bold uppercase tracking-wide text-cyan-glow">
            Tu privacidad
          </h2>
        </div>
        <p className="font-mono text-xs text-muted-foreground leading-relaxed mb-4">
          Solo usamos almacenamiento técnico esencial (tu sesión de inicio de sesión). Sin cookies
          de analítica ni publicidad. Más info en la{" "}
          <Link to="/politica-de-cookies" className="text-cyan-glow hover:underline">
            política de cookies
          </Link>{" "}
          y la{" "}
          <Link to="/politica-de-privacidad" className="text-cyan-glow hover:underline">
            política de privacidad
          </Link>
          .
        </p>
        <button
          type="button"
          onClick={dismiss}
          className="w-full font-mono text-xs font-bold uppercase tracking-wide border border-cyan-glow/50 text-cyan-glow px-4 py-2 hover:bg-cyan-glow/10 transition-colors"
        >
          Entendido
        </button>
      </div>
    </div>
  );
}
