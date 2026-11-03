import { Link, useNavigate } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { AlertTriangle, Clock, Eye, Search } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/useAuth";
import { ApiError } from "@/services/api/client";
import {
  isProfileIncompleteError,
  submissionsApi,
  type LinkCheckResult,
} from "@/services/api/submissions";
import { formatPrice } from "@/lib/format";
import { loginSearch } from "@/lib/safe-redirect";

interface LinkCheckStepProps {
  initialUrl?: string;
  onContinue: (result: LinkCheckResult, url: string) => void;
  onProfileIncomplete?: () => void;
}

const MAX_URL = 2048;

export function LinkCheckStep({
  initialUrl = "",
  onContinue,
  onProfileIncomplete,
}: LinkCheckStepProps) {
  const nav = useNavigate();
  const { refreshMe } = useAuth();
  const [url, setUrl] = useState(initialUrl);
  const [inlineError, setInlineError] = useState<string | null>(null);
  const [result, setResult] = useState<LinkCheckResult | null>(null);
  const [checkedUrl, setCheckedUrl] = useState("");

  useEffect(() => {
    setUrl(initialUrl);
  }, [initialUrl]);

  const mutation = useMutation({
    mutationFn: (value: string) => submissionsApi.checkLink(value),
    onSuccess: (data, value) => {
      setResult(data);
      if (data.status === "ok" && !data.previously_published) onContinue(data, value);
    },
    onError: (error, value) => {
      if (error instanceof ApiError && error.status === 401) {
        void nav({
          to: "/login",
          search: loginSearch(`/publicar?url=${encodeURIComponent(value)}`),
        });
        return;
      }
      if (isProfileIncompleteError(error)) {
        void refreshMe();
        onProfileIncomplete?.();
        return;
      }
      if (error instanceof ApiError && error.status === 400) {
        setInlineError(error.message || "El enlace no es válido.");
        return;
      }
      setInlineError("No se pudo comprobar el enlace. Inténtalo de nuevo.");
    },
  });

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const value = url.trim();
    if (!value) {
      setInlineError("Pega el enlace del chollo.");
      return;
    }
    if (value.length > MAX_URL) {
      setInlineError("El enlace es demasiado largo.");
      return;
    }
    setCheckedUrl(value);
    setInlineError(null);
    setResult(null);
    mutation.mutate(value);
  };

  const existing = result?.existing_deal;

  return (
    <div className="space-y-4">
      <form onSubmit={onSubmit} className="space-y-3" noValidate>
        <label
          htmlFor="publish-url"
          className="block text-xs font-mono uppercase text-muted-foreground"
        >
          Enlace del chollo
        </label>
        <input
          id="publish-url"
          type="url"
          inputMode="url"
          autoFocus
          autoComplete="off"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.amazon.es/..."
          aria-invalid={inlineError ? true : undefined}
          aria-describedby={inlineError ? "publish-url-error" : undefined}
          className="w-full bg-surface-900 border border-surface-700 px-4 py-4 font-mono text-base outline-none focus:border-cyan-glow text-foreground"
        />
        {inlineError && (
          <p id="publish-url-error" role="alert" className="text-sm text-alert-red">
            {inlineError}
          </p>
        )}
        <button
          type="submit"
          disabled={mutation.isPending}
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-6 py-3 hover:bg-foreground transition-colors disabled:opacity-50"
        >
          <Search className="size-4" aria-hidden="true" />
          Comprobar
        </button>
      </form>

      {mutation.isPending && (
        <div role="status" aria-label="Comprobando enlace" className="space-y-2">
          <Skeleton className="h-5 w-2/3" />
          <Skeleton className="h-16 w-full" />
        </div>
      )}

      {result?.status === "published" && existing && (
        <div className="border border-surface-700 bg-surface-800 p-4 space-y-3">
          <p className="text-sm">Este chollo ya está publicado.</p>
          <div className="flex items-center gap-3">
            {existing.image_url && (
              <img
                src={existing.image_url}
                alt=""
                className="size-16 object-contain bg-white shrink-0"
                loading="lazy"
              />
            )}
            <div className="min-w-0">
              <p className="font-bold text-sm line-clamp-2">{existing.title}</p>
              <p className="font-mono text-cyan-glow">{formatPrice(existing.current_price)}</p>
            </div>
          </div>
          <Link
            to="/chollo/$slug"
            params={{ slug: existing.slug }}
            className="inline-block text-cyan-glow font-mono text-xs font-bold hover:underline"
          >
            Ver y votar
          </Link>
        </div>
      )}

      {result?.status === "upcoming" && (
        <div className="flex gap-3 border border-surface-700 bg-surface-800 p-4">
          <Clock className="size-5 shrink-0 text-cyan-glow" aria-hidden="true" />
          <p className="text-sm">
            Este chollo está programado y se publicará próximamente. No hace falta que lo envíes.
          </p>
        </div>
      )}

      {result?.status === "in_review" && (
        <div className="flex gap-3 border border-surface-700 bg-surface-800 p-4">
          <Eye className="size-5 shrink-0 text-cyan-glow" aria-hidden="true" />
          <p className="text-sm">
            Este chollo ya está en revisión. Gracias por compartirlo, lo revisaremos pronto.
          </p>
        </div>
      )}

      {result?.status === "ok" && result.previously_published && (
        <div className="flex gap-3 border border-surface-700 bg-surface-800 p-4">
          <AlertTriangle className="size-5 shrink-0 text-cyan-glow" aria-hidden="true" />
          <p className="text-sm">
            Este producto se publicó antes, pero ya no está activo. Puedes volver a proponerlo.
          </p>
          <button
            type="button"
            onClick={() => onContinue(result, checkedUrl)}
            className="ml-auto shrink-0 self-center bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2 hover:bg-foreground transition-colors"
          >
            Continuar
          </button>
        </div>
      )}
    </div>
  );
}
