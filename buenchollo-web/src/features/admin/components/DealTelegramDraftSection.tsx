/** Publicación de Telegram dentro de «Editar chollo»: último envío registrado,
 *  generación del borrador con el motor de IA elegido y el texto editable que
 *  se guarda en el chollo con GUARDAR. El envío sigue en el panel de Telegram. */
import { useEffect, useState } from "react";
import { History, Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { errorMessage } from "@/lib/errors";
import { formatPrice, formatRelativeTime } from "@/lib/format";
import {
  telegramApi,
  type TelegramGenerateRequest,
  type TelegramPublication,
} from "@/services/api/telegram";
import { adminInputCls as inputCls, appendHashtags } from "../deal-form";
import type { AiProvider } from "@/lib/ai-providers";
import { AiProviderSelect } from "./AiProviderSelect";

const CHANNEL_LABEL: Record<TelegramPublication["channel_kind"], string> = {
  main: "canal general",
  admin: "canal Admin",
  other: "otro canal",
};

interface Props {
  readonly dealId: string;
  readonly value: string;
  readonly onChange: (value: string) => void;
  /** Datos actuales del formulario para la plantilla del post. */
  readonly buildRequest: () => TelegramGenerateRequest;
  readonly provider: AiProvider;
  readonly onProviderChange: (value: AiProvider) => void;
}

export function DealTelegramDraftSection({
  dealId,
  value,
  onChange,
  buildRequest,
  provider,
  onProviderChange,
}: Props) {
  const [generating, setGenerating] = useState(false);
  const [last, setLast] = useState<TelegramPublication | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLast(null);
    telegramApi
      .latestPublication(dealId)
      .then((publication) => {
        if (!cancelled) setLast(publication);
      })
      .catch(() => {
        if (!cancelled) setLast(null);
      });
    return () => {
      cancelled = true;
    };
  }, [dealId]);

  const generate = async () => {
    setGenerating(true);
    try {
      const result = await telegramApi.generate({
        ...buildRequest(),
        ai_copy: true,
        provider,
      });
      onChange(appendHashtags(result.text, result.suggested_categories ?? []));
      if (result.ai_copy) {
        toast.success("Publicación generada: revísala y pulsa GUARDAR");
      } else {
        toast.warning("La IA no respondió: se ha usado la descripción corta");
      }
    } catch (e: unknown) {
      toast.error(errorMessage(e));
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="border border-surface-700 p-3 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-mono text-xs uppercase text-cyan-glow">Publicación Telegram</span>
        <AiProviderSelect
          id="telegram-ai-provider"
          value={provider}
          onChange={onProviderChange}
          disabled={generating}
        />
      </div>

      {last ? (
        <details className="bg-surface-900 border border-surface-700 px-3 py-2">
          <summary className="font-mono text-[11px] text-muted-foreground cursor-pointer flex flex-wrap items-center gap-x-2">
            <History className="size-3.5 inline" />
            Último envío {formatRelativeTime(last.sent_at)} (
            {new Date(last.sent_at).toLocaleString("es-ES")}) · {CHANNEL_LABEL[last.channel_kind]}
            {last.price != null && <> · a {formatPrice(last.price)}</>}
          </summary>
          <pre className="mt-2 whitespace-pre-wrap break-words font-mono text-xs text-foreground/80">
            {last.text}
          </pre>
          {last.repriced_text && last.repriced_text !== last.text && (
            <button
              type="button"
              onClick={() => onChange(last.repriced_text ?? "")}
              className="mt-2 border border-surface-600 px-3 py-1.5 font-mono text-[11px] hover:border-cyan-glow"
            >
              Usar este texto con el precio actual
            </button>
          )}
        </details>
      ) : (
        <p className="font-mono text-[10px] text-muted-foreground">
          Sin envíos registrados a Telegram para este chollo.
        </p>
      )}

      <button
        type="button"
        onClick={generate}
        disabled={generating}
        className="w-full sm:w-auto border border-cyan-glow/50 text-cyan-glow font-mono text-xs px-4 py-2 flex items-center justify-center gap-2 hover:bg-cyan-glow/10 disabled:opacity-50"
      >
        {generating ? (
          <Loader2 className="size-3.5 animate-spin" />
        ) : (
          <Sparkles className="size-3.5" />
        )}
        {generating ? "GENERANDO…" : value.trim() ? "REGENERAR PUBLICACIÓN" : "GENERAR PUBLICACIÓN"}
      </button>

      <textarea
        aria-label="Texto de la publicación de Telegram"
        placeholder="Sin publicación guardada. Genera una o escríbela aquí."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        maxLength={4096}
        rows={value ? 10 : 3}
        className={inputCls + " font-mono text-xs"}
      />
      <p className="font-mono text-[10px] text-muted-foreground">
        Se guarda en el chollo con GUARDAR. Para enviarla, usa 🚀 Publicar en Telegram: el panel se
        abre con este texto.
      </p>
    </div>
  );
}
