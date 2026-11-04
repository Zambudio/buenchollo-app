import { Copy } from "lucide-react";
import { toast } from "sonner";

interface CouponCodeProps {
  code: string | null | undefined;
}

export function CouponCode({ code }: CouponCodeProps) {
  if (!code) return null;

  const copy = async () => {
    try {
      if (typeof navigator === "undefined" || !navigator.clipboard) throw new Error("no clipboard");
      await navigator.clipboard.writeText(code);
      toast.success("Código copiado");
    } catch {
      toast.error("No se pudo copiar. Selecciona el código y cópialo manualmente.");
    }
  };

  return (
    <div className="coupon-code mb-4 flex items-stretch border border-dashed border-cyan-glow/60 bg-surface-900">
      <div className="min-w-0 flex-1 px-3 py-2">
        <div className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          Código de descuento
        </div>
        <code className="block font-mono text-base font-bold break-all select-all">{code}</code>
      </div>
      <button
        type="button"
        onClick={copy}
        className="shrink-0 inline-flex items-center gap-1.5 px-4 font-mono text-xs font-bold bg-cyan-glow text-surface-900 hover:bg-foreground transition-colors"
      >
        <Copy className="size-3.5" aria-hidden="true" />
        Copiar
      </button>
    </div>
  );
}
