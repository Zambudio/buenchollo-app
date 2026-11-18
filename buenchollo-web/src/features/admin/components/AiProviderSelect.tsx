/** Selector del motor de IA del admin (autocompletado y publicación de Telegram). */
import { Bot } from "lucide-react";
import { AI_PROVIDER_OPTIONS, isAiProvider, type AiProvider } from "@/lib/ai-providers";

interface Props {
  readonly id: string;
  readonly value: AiProvider;
  readonly onChange: (value: AiProvider) => void;
  readonly disabled?: boolean;
}

export function AiProviderSelect({ id, value, onChange, disabled }: Props) {
  return (
    <div className="flex items-center gap-2 min-w-0">
      <Bot className="size-3.5 text-cyan-glow shrink-0" />
      <label
        htmlFor={id}
        className="font-mono text-[10px] uppercase text-muted-foreground shrink-0"
      >
        Motor IA:
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => {
          if (isAiProvider(e.target.value)) onChange(e.target.value);
        }}
        disabled={disabled}
        className="min-w-0 bg-surface-900 border border-surface-700 text-foreground font-mono text-xs px-2 py-1 outline-none focus:border-cyan-glow disabled:opacity-50"
      >
        {AI_PROVIDER_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}
