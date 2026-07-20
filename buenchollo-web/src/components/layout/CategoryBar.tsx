import { Link } from "@tanstack/react-router";
import { FolderTree, ListFilter, Newspaper, Send } from "lucide-react";

const LINKS = [
  { label: "Filtros", to: "/explorar" as const, icon: ListFilter },
  { label: "Categorías", to: "/categorias" as const, icon: FolderTree },
  { label: "Blog", to: "/blog" as const, icon: Newspaper },
];

const TELEGRAM_URL = "https://t.me/buenchollotech";

export function CategoryBar() {
  return (
    <nav
      aria-label="Navegación de chollos"
      className="bg-surface-800 border-b border-surface-700 overflow-x-auto"
    >
      <div className="max-w-7xl mx-auto px-2 sm:px-6 flex items-center justify-between gap-2 sm:gap-6 whitespace-nowrap">
        <div className="flex items-center gap-3 sm:gap-6">
          {LINKS.map(({ label, to, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className="flex items-center gap-1.5 font-mono text-[11px] sm:text-xs uppercase tracking-wide text-muted-foreground hover:text-cyan-glow py-2.5 transition-colors"
              activeProps={{ className: "text-cyan-glow" }}
            >
              {Icon && <Icon className="size-3.5" aria-hidden="true" />}
              {label}
            </Link>
          ))}
        </div>
        <a
          href={TELEGRAM_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 my-2 rounded-full bg-[#229ED9] hover:bg-[#1c8bc0] text-white font-mono text-[11px] sm:text-xs font-bold uppercase tracking-wide px-3 sm:px-3.5 py-1.5 shadow-[0_0_12px_rgba(34,158,217,0.5)] transition-colors shrink-0"
        >
          <Send className="size-3.5" />
          <span className="sm:hidden">Telegram</span>
          <span className="hidden sm:inline">Chollos en Telegram</span>
        </a>
      </div>
    </nav>
  );
}
