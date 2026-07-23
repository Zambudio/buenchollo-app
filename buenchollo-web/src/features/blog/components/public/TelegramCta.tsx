import { Send } from "lucide-react";

const TELEGRAM_URL = "https://t.me/buenchollotech";

export function TelegramCta({ compact = false }: { compact?: boolean }) {
  if (compact) {
    return (
      <div className="not-prose border border-cyan-glow/40 bg-surface-800/60 rounded-lg px-4 py-3 flex items-center justify-between flex-wrap gap-3">
        <p className="text-xs text-muted-foreground">
          <span className="font-mono uppercase text-cyan-glow">Telegram · </span>
          No te pierdas ningún chollo.
        </p>
        <a
          href={TELEGRAM_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 bg-cyan-glow text-surface-900 font-mono text-[11px] font-bold px-3 py-1.5 hover:bg-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-glow shrink-0"
        >
          <Send className="size-3.5" /> Unirme
        </a>
      </div>
    );
  }

  return (
    <div className="not-prose border border-cyan-glow/40 bg-surface-800/60 rounded-lg text-center p-6 my-8">
      <p className="font-mono text-xs uppercase text-cyan-glow mb-2">No te pierdas ningún chollo</p>
      <p className="text-sm text-muted-foreground mb-3">
        Únete a nuestro canal de Telegram y recibe las mejores ofertas al instante.
      </p>
      <a
        href={TELEGRAM_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2 hover:bg-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-glow"
      >
        <Send className="size-4" /> Unirme al canal
      </a>
    </div>
  );
}
