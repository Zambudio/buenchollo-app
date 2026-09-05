/** Panel "Autocompletar desde Amazon" del admin (TD-03). */
import { Bot, Loader2, Wand2 } from "lucide-react";
import { adminInputCls as inputCls } from "../deal-form";

interface Props {
  readonly url: string;
  readonly busy: boolean;
  readonly provider: string;
  readonly onUrlChange: (value: string) => void;
  readonly onProviderChange: (value: string) => void;
  readonly onAutofill: () => void;
}

export function AmazonAutofillPanel({
  url,
  busy,
  provider,
  onUrlChange,
  onProviderChange,
  onAutofill,
}: Props) {
  return (
    <div className="bg-surface-800 border border-cyan-glow/40 p-4 mb-4">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <Wand2 className="size-4 text-cyan-glow" />
          <h3 className="font-mono text-xs uppercase text-cyan-glow">Autocompletar desde Amazon</h3>
        </div>
        <div className="flex items-center gap-2">
          <Bot className="size-3.5 text-cyan-glow" />
          <label
            htmlFor="ai-provider"
            className="font-mono text-[10px] uppercase text-muted-foreground"
          >
            Motor IA:
          </label>
          <select
            id="ai-provider"
            value={provider}
            onChange={(e) => onProviderChange(e.target.value)}
            disabled={busy}
            className="bg-surface-900 border border-surface-700 text-foreground font-mono text-xs px-2 py-1 outline-none focus:border-cyan-glow disabled:opacity-50"
          >
            <option value="omniroute">OmniRoute (Modelos Gratuitos)</option>
            <option value="openai">OpenAI (GPT-4o Oficial)</option>
            <option value="auto">Automático (OmniRoute + Fallback)</option>
          </select>
        </div>
      </div>
      <p className="font-mono text-[10px] text-muted-foreground mb-3">
        Pega tu URL de afiliado de Amazon y rellenaremos título, imagen, marca, copywriting y
        precios automáticamente.
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
          className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2 flex items-center justify-center gap-2 hover:bg-foreground disabled:opacity-50 transition-colors whitespace-nowrap"
        >
          {busy ? <Loader2 className="size-4 animate-spin" /> : <Wand2 className="size-4" />}
          {busy ? "PROCESANDO..." : "AUTOCOMPLETAR"}
        </button>
      </div>
    </div>
  );
}
