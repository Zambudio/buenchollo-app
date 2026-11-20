import { TELEGRAM_URL, WHATSAPP_URL } from "@/lib/site";
import { Link } from "@tanstack/react-router";
import { Compass, House, Newspaper, Send, Trophy } from "lucide-react";
import { WhatsAppIcon } from "./WhatsAppIcon";

const LINKS = [
  { label: "Inicio", to: "/" as const, icon: House },
  { label: "Chollos", to: "/explorar" as const, icon: Compass },
  { label: "Tops y categorías", to: "/categorias" as const, icon: Trophy },
  { label: "Blog", to: "/blog" as const, icon: Newspaper },
];

export function CategoryBar() {
  return (
    <nav
      aria-label="Navegación de chollos"
      className="site-nav bg-surface-800 border-b border-surface-700 overflow-x-auto"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between gap-2 sm:gap-6 whitespace-nowrap">
        <div className="flex items-center gap-1 sm:gap-2">
          {LINKS.map(({ label, to, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className="site-nav-link flex items-center gap-1.5 text-xs sm:text-sm font-semibold text-muted-foreground hover:text-cyan-glow py-3 transition-colors"
              activeProps={{ className: "text-cyan-glow" }}
            >
              {Icon && <Icon className="size-4" aria-hidden="true" />}
              {label}
            </Link>
          ))}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <a
            href={TELEGRAM_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="site-nav-channel flex items-center gap-1.5 my-2 text-xs sm:text-sm font-semibold px-3 sm:px-3.5 py-1.5 transition-colors"
          >
            <Send className="size-3.5" aria-hidden="true" />
            Telegram
          </a>
          <a
            href={WHATSAPP_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="site-nav-channel flex items-center gap-1.5 my-2 text-xs sm:text-sm font-semibold px-3 sm:px-3.5 py-1.5 transition-colors"
          >
            <WhatsAppIcon className="size-3.5" />
            WhatsApp
          </a>
        </div>
      </div>
    </nav>
  );
}
