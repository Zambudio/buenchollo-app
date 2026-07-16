/** Panel "Autocompletar desde Amazon" del admin (TD-03). */
import { Loader2, Wand2 } from "lucide-react";
import { adminInputCls as inputCls } from "../deal-form";

interface Props {
  readonly url: string;
  readonly busy: boolean;
  readonly onUrlChange: (value: string) => void;
  readonly onAutofill: () => void;
}

export function AmazonAutofillPanel({ url, busy, onUrlChange, onAutofill }: Props) {
  return (
    <div className="bg-surface-800 border border-cyan-glow/40 p-4 mb-4">
      <div className="flex items-center gap-2 mb-2">
        <Wand2 className="size-4 text-cyan-glow" />
        <h3 className="font-mono text-xs uppercase text-cyan-glow">Autocompletar desde Amazon</h3>
      </div>
      <p className="font-mono text-[10px] text-muted-foreground mb-3">
        Pega tu URL de afiliado de Amazon y rellenaremos título, imagen, marca y precios
        automáticamente.
      </p>
      <div className="flex flex-col sm:flex-row gap-2">
        <input
          type="url"
          placeholder="https://www.amazon.es/dp/..."
          value={url}
          onChange={(e) => onUrlChange(e.target.value)}
          className={inputCls + " flex-1"}
        />
        <button
          type="button"
          onClick={onAutofill}
          disabled={busy}
          className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2 flex items-center justify-center gap-2 hover:bg-foreground disabled:opacity-50"
        >
          {busy ? <Loader2 className="size-4 animate-spin" /> : <Wand2 className="size-4" />}
          {busy ? "PROCESANDO..." : "[ AUTOCOMPLETAR ]"}
        </button>
      </div>
    </div>
  );
}
