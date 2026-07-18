import { useState, type ReactNode } from "react";
import { Link2, Check, Share2 } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from "@/components/ui/dialog";

interface ShareDialogProps {
  url: string;
  title: string;
  price?: number | null;
  trigger: ReactNode;
}

export function ShareDialog({ url, title, price, trigger }: ShareDialogProps) {
  const [copied, setCopied] = useState(false);

  const shareUrl =
    typeof window !== "undefined" && !url.startsWith("http")
      ? `${window.location.origin}${url}`
      : url;

  const text = price ? `🔥 ${title} — ${price.toFixed(2).replace(".", ",")}€` : `🔥 ${title}`;

  const enc = encodeURIComponent;
  const links = {
    whatsapp: `https://wa.me/?text=${enc(text + " " + shareUrl)}`,
    telegram: `https://t.me/share/url?url=${enc(shareUrl)}&text=${enc(text)}`,
    facebook: `https://www.facebook.com/sharer/sharer.php?u=${enc(shareUrl)}`,
    x: `https://twitter.com/intent/tweet?text=${enc(text)}&url=${enc(shareUrl)}`,
  };

  const copy = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      toast.success("Enlace copiado");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("No se pudo copiar");
    }
  };

  const platformBtn =
    "inline-flex items-center justify-center gap-2 px-3 py-3 font-mono text-xs font-bold uppercase tracking-wide text-white transition-colors";

  return (
    <Dialog>
      <DialogTrigger asChild onClick={(e: React.MouseEvent) => e.stopPropagation()}>
        {trigger}
      </DialogTrigger>
      <DialogContent className="bg-surface-800 border-surface-700 text-foreground max-w-sm">
        <DialogHeader>
          <div className="mx-auto mb-1 flex size-11 items-center justify-center rounded-full bg-cyan-glow/10 border border-cyan-glow/30">
            <Share2 className="size-5 text-cyan-glow" />
          </div>
          <DialogTitle className="text-center font-mono uppercase tracking-wide text-base">
            Compartir chollo
          </DialogTitle>
          <DialogDescription className="text-center font-mono text-xs">
            ¡Que nadie se pierda esta oferta!
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-2">
          <a
            href={links.whatsapp}
            target="_blank"
            rel="noopener noreferrer"
            className={`${platformBtn} bg-[#25D366] hover:bg-[#1fbd5a]`}
          >
            <svg viewBox="0 0 24 24" className="size-4 fill-current" aria-hidden>
              <path d="M17.5 14.4c-.3-.1-1.7-.8-2-.9-.3-.1-.5-.1-.7.2-.2.3-.7.9-.9 1.1-.2.2-.3.2-.6.1-.3-.1-1.2-.5-2.4-1.5-.9-.8-1.5-1.8-1.6-2.1-.2-.3 0-.5.1-.6.1-.1.3-.3.4-.5.1-.2.2-.3.3-.5.1-.2 0-.4 0-.5 0-.1-.7-1.6-.9-2.2-.2-.6-.5-.5-.7-.5h-.6c-.2 0-.5.1-.8.4-.3.3-1 1-1 2.5s1.1 2.9 1.2 3.1c.1.2 2.1 3.3 5.2 4.6.7.3 1.3.5 1.7.6.7.2 1.4.2 1.9.1.6-.1 1.7-.7 2-1.4.2-.7.2-1.3.2-1.4-.1-.1-.3-.2-.6-.3zM12 2C6.5 2 2 6.5 2 12c0 1.8.5 3.5 1.3 4.9L2 22l5.3-1.3c1.4.8 3 1.2 4.7 1.2 5.5 0 10-4.5 10-10S17.5 2 12 2zm0 18.2c-1.5 0-3-.4-4.3-1.2l-.3-.2-3.2.8.9-3.1-.2-.3C4 14.9 3.5 13.5 3.5 12c0-4.7 3.8-8.5 8.5-8.5s8.5 3.8 8.5 8.5-3.8 8.2-8.5 8.2z" />
            </svg>
            WhatsApp
          </a>
          <a
            href={links.telegram}
            target="_blank"
            rel="noopener noreferrer"
            className={`${platformBtn} bg-[#229ED9] hover:bg-[#1c8bc0]`}
          >
            <svg viewBox="0 0 24 24" className="size-4 fill-current" aria-hidden>
              <path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z" />
            </svg>
            Telegram
          </a>
          <a
            href={links.facebook}
            target="_blank"
            rel="noopener noreferrer"
            className={`${platformBtn} bg-[#1877F2] hover:bg-[#1465d6]`}
          >
            <svg viewBox="0 0 24 24" className="size-4 fill-current" aria-hidden>
              <path d="M22 12c0-5.52-4.48-10-10-10S2 6.48 2 12c0 4.84 3.44 8.87 8 9.8V15H8v-3h2V9.5C10 7.57 11.57 6 13.5 6H16v3h-2c-.55 0-1 .45-1 1v2h3v3h-3v6.95c5.05-.5 9-4.76 9-9.95z" />
            </svg>
            Facebook
          </a>
          <a
            href={links.x}
            target="_blank"
            rel="noopener noreferrer"
            className={`${platformBtn} bg-black border border-surface-600 hover:bg-surface-900`}
          >
            <svg viewBox="0 0 24 24" className="size-4 fill-current" aria-hidden>
              <path d="M18.244 2H21l-6.52 7.45L22 22h-6.84l-4.78-6.24L4.8 22H2.04l6.98-7.97L2 2h6.92l4.32 5.71L18.24 2zm-2.4 18h1.5L7.27 4H5.66l10.18 16z" />
            </svg>
            X (Twitter)
          </a>
        </div>

        <div className="flex items-center gap-2 bg-surface-900 border border-surface-700 px-3 py-2.5 font-mono text-xs text-muted-foreground overflow-hidden">
          <Link2 className="size-4 shrink-0 text-cyan-glow" />
          <span className="truncate flex-1">{shareUrl}</span>
          <button
            type="button"
            onClick={copy}
            className={`shrink-0 inline-flex items-center gap-1.5 border border-surface-700 hover:border-cyan-glow hover:text-cyan-glow px-2 py-1.5 font-mono text-[10px] uppercase transition-colors ${copied ? "border-cyan-glow text-cyan-glow" : ""}`}
          >
            {copied ? (
              <>
                <Check className="size-3.5" /> Copiado
              </>
            ) : (
              <>
                <Link2 className="size-3.5" /> Copiar
              </>
            )}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
