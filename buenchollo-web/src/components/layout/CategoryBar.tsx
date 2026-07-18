import { Link } from "@tanstack/react-router";

const LINKS = [
  { label: "Categorías", to: "/categorias" as const },
  { label: "Ofertas", to: "/explorar" as const },
  { label: "Blog", to: "/blog" as const },
];

export function CategoryBar() {
  return (
    <nav
      aria-label="Categorías"
      className="bg-surface-800 border-b border-surface-700 overflow-x-auto"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between gap-6 whitespace-nowrap">
        <div className="flex items-center gap-6">
          {LINKS.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              className="font-mono text-xs uppercase tracking-wide text-muted-foreground hover:text-cyan-glow py-2.5 transition-colors"
              activeProps={{ className: "text-cyan-glow" }}
            >
              {l.label}
            </Link>
          ))}
        </div>
        <Link
          to="/explorar"
          className="font-mono text-xs uppercase tracking-wide text-cyan-glow hover:text-foreground py-2.5 transition-colors"
        >
          [ FILTRAR ]
        </Link>
      </div>
    </nav>
  );
}
