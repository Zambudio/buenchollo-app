import { Link } from "@tanstack/react-router";
import { ArrowUpRight, Compass, House, Newspaper, Send, Trophy } from "lucide-react";

const LINKS = [
  { label: "Inicio", to: "/" as const, icon: House },
  { label: "Chollos", to: "/explorar" as const, icon: Compass },
  { label: "Tops y categorías", to: "/categorias" as const, icon: Trophy },
  { label: "Blog", to: "/blog" as const, icon: Newspaper },
];

const TELEGRAM_URL = "https://t.me/buenchollotech";

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
        <a
          href={TELEGRAM_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="site-nav-telegram flex items-center gap-1.5 my-2 text-xs sm:text-sm font-semibold px-3 sm:px-3.5 py-1.5 transition-colors shrink-0"
        >
          <Send className="size-3.5" />
          <span className="sm:hidden">Telegram</span>
          <span className="hidden sm:inline">Telegram</span>
          <ArrowUpRight className="hidden sm:block size-3.5" />
        </a>
      </div>
    </nav>
  );
}
