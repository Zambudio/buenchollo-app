import type { TocEntry } from "@/services/api/blog";

export function TableOfContents({ toc }: { toc: TocEntry[] }) {
  if (toc.length < 2) return null;
  return (
    <nav
      aria-label="Tabla de contenidos"
      className="not-prose border border-surface-700 bg-surface-800/50 rounded p-4 mb-6"
    >
      <p className="font-mono text-xs uppercase text-cyan-glow mb-2">Contenido</p>
      <ol className="space-y-1 text-sm">
        {toc.map((entry) => (
          <li key={entry.id} className={entry.level === 3 ? "ml-4" : ""}>
            <a href={`#${entry.id}`} className="text-muted-foreground hover:text-cyan-glow">
              {entry.text}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}
