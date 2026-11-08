/** Resultado de importar una URL de Awin / Tradedoubler en el editor.
 *  Distingue tres etapas: enlace generado → producto importado → lista para
 *  publicar (esta última la decide la validación del formulario). */
import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  Link2,
  Loader2,
  Package,
  Send,
  X,
} from "lucide-react";
import { IMPORT_FIELD_LABELS, adminInputCls as inputCls, type ImportConflict } from "../deal-form";
import type { ImportResponse } from "@/services/api/affiliates";

const STATUS_LABELS: Record<string, string> = {
  unsupported_store: "Tienda no configurada",
  use_amazon_flow: "Amazon",
  program_choice_required: "Elige programa",
  program_disabled: "Programa deshabilitado",
  not_configured: "Sin configurar",
  pending_approval: "Pendiente de aprobación",
  catalog_unavailable: "Catálogo no disponible",
  no_match: "Sin coincidencia",
  ambiguous: "Coincidencia ambigua",
  rate_limited: "Límite de API",
  provider_error: "Error de la red",
  link_only: "Solo enlace",
  imported: "Producto importado",
  stale_data: "Datos caducados",
};

const MISSING_LABELS: Record<string, string> = {
  affiliate_url: "enlace afiliado",
  title: "título",
  current_price: "precio actual",
  previous_price_evidence: "precio anterior con evidencia",
  shipping_info: "envío",
  image_url: "imagen",
  description: "descripción",
  availability: "disponibilidad",
  category: "categoría",
};

const BAD = new Set([
  "unsupported_store",
  "program_disabled",
  "not_configured",
  "pending_approval",
  "rate_limited",
  "provider_error",
]);

function formatAge(iso: string | null | undefined): string {
  if (!iso) return "fecha desconocida";
  const d = new Date(iso);
  const hours = Math.round((Date.now() - d.getTime()) / 36e5);
  const when = d.toLocaleString("es-ES", { dateStyle: "short", timeStyle: "short" });
  return hours < 1 ? `${when} (hace <1 h)` : `${when} (hace ${hours} h)`;
}

interface Props {
  readonly result: ImportResponse;
  readonly conflicts: ImportConflict[];
  readonly ready: boolean;
  readonly busy: boolean;
  readonly onChooseProgram: (programId: string) => void;
  readonly onChooseCandidate: (productKey: string) => void;
  readonly onSearchIds: (ids: { ean?: string; sku?: string }) => void;
  readonly onResolveConflict: (conflict: ImportConflict) => void;
  readonly onOpenExisting: (dealId: string) => void;
  readonly onDismiss: () => void;
}

function Step({ done, label, icon }: { done: boolean; label: string; icon: React.ReactNode }) {
  return (
    <li
      className={`flex items-center gap-1.5 font-mono text-[11px] uppercase ${done ? "text-cyan-glow" : "text-muted-foreground"}`}
    >
      {done ? <CheckCircle2 className="size-3.5" /> : <Circle className="size-3.5" />}
      {icon}
      {label}
    </li>
  );
}

export function AffiliateImportPanel({
  result,
  conflicts,
  ready,
  busy,
  onChooseProgram,
  onChooseCandidate,
  onSearchIds,
  onResolveConflict,
  onOpenExisting,
  onDismiss,
}: Props) {
  const [ean, setEan] = useState("");
  const [sku, setSku] = useState("");
  const linkDone = !!result.link?.affiliate_url;
  const productDone = result.stage === "product_imported";
  const bad = BAD.has(result.status);

  return (
    <section
      aria-label="Resultado de la importación"
      className={`bg-surface-800 border p-4 mb-4 space-y-3 ${bad ? "border-alert-red/60" : "border-cyan-glow/40"}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-mono text-xs uppercase text-cyan-glow">
            {result.program ? `${result.program.name} · ${result.program.network}` : "Importación"}
            <span
              className={`ml-2 px-1.5 py-0.5 text-[10px] ${bad ? "bg-alert-red/20 text-alert-red" : "bg-cyan-glow/15 text-cyan-glow"}`}
            >
              {STATUS_LABELS[result.status] ?? result.status}
            </span>
          </p>
          <p className="font-mono text-[11px] text-muted-foreground mt-1 break-words">
            {result.message}
          </p>
        </div>
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Cerrar resultado"
          className="p-1 hover:text-cyan-glow"
        >
          <X className="size-4" />
        </button>
      </div>

      <ol className="flex flex-wrap gap-x-4 gap-y-1" aria-label="Etapas">
        <Step done={linkDone} label="Enlace generado" icon={<Link2 className="size-3.5" />} />
        <Step
          done={productDone}
          label="Producto importado"
          icon={<Package className="size-3.5" />}
        />
        <Step done={ready} label="Lista para publicar" icon={<Send className="size-3.5" />} />
      </ol>

      {result.program && (
        <p className="font-mono text-[10px] text-muted-foreground">
          Adhesión: <strong>{result.program.membership_status}</strong>
          {result.program.membership_checked_at
            ? ` · comprobada ${formatAge(result.program.membership_checked_at)}`
            : " · sin comprobar"}
          {result.link?.source ? ` · enlace: ${result.link.source}` : ""}
        </p>
      )}
      {!linkDone && result.link?.message && (
        <p className="font-mono text-[11px] text-alert-red">Enlace: {result.link.message}</p>
      )}

      {result.provenance && productDone && (
        <p className="font-mono text-[10px] text-muted-foreground">
          Fuente: {result.provenance.data_source}
          {result.provenance.feed_id ? ` (feed ${result.provenance.feed_id})` : ""} · dato del
          proveedor: {formatAge(result.provenance.provider_updated_at)} · importado:{" "}
          {formatAge(result.provenance.imported_at)}
          {result.provenance.freshness === "stale" && (
            <span className="text-alert-red">
              {" "}
              · CADUCADO (máx. {result.provenance.max_data_age_hours} h)
            </span>
          )}
        </p>
      )}

      {result.offer?.rrp_price && (
        <p className="font-mono text-[10px] text-muted-foreground">
          PVP recomendado del feed: {result.offer.rrp_price} € — no se usa como precio anterior.
        </p>
      )}

      {result.missing.length > 0 && (
        <p className="font-mono text-[11px]">
          <span className="text-muted-foreground">Pendiente de completar: </span>
          {result.missing.map((m) => MISSING_LABELS[m] ?? m).join(", ")}
        </p>
      )}

      {result.warnings.map((w) => (
        <p key={w} className="font-mono text-[10px] text-amber-700 dark:text-yellow-400 flex gap-1">
          <AlertTriangle className="size-3 shrink-0 mt-0.5" /> {w}
        </p>
      ))}

      {result.existing_deal && (
        <div className="font-mono text-[11px] border border-surface-700 p-2 flex flex-wrap items-center gap-2">
          Ya existe un chollo de este producto:{" "}
          <strong className="break-words">{result.existing_deal.title}</strong> (
          {result.existing_deal.status}).
          <button
            type="button"
            onClick={() => onOpenExisting(result.existing_deal!.id)}
            className="border border-cyan-glow/50 text-cyan-glow px-2 py-1 hover:bg-cyan-glow/10"
          >
            EDITAR EL EXISTENTE
          </button>
        </div>
      )}

      {result.program_options.length > 0 && (
        <div className="space-y-1">
          <p className="font-mono text-[11px] text-muted-foreground">Elige el programa correcto:</p>
          <div className="flex flex-wrap gap-2">
            {result.program_options.map((p) => (
              <button
                key={p.id}
                type="button"
                disabled={busy}
                onClick={() => onChooseProgram(p.id)}
                className="border border-surface-700 px-3 py-1.5 font-mono text-xs hover:border-cyan-glow disabled:opacity-50 text-left"
              >
                {p.name} · {p.advertiser_id} · {p.membership_status}
              </button>
            ))}
          </div>
        </div>
      )}

      {result.candidates.length > 0 && (
        <div className="space-y-1">
          <p className="font-mono text-[11px] text-muted-foreground">
            {result.status === "ambiguous"
              ? "Varias variantes coinciden con la URL. Elige la correcta:"
              : "Candidatos por título (no se ha elegido ninguno):"}
          </p>
          <ul className="space-y-1">
            {result.candidates.map((c) => (
              <li key={c.product_key}>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onChooseCandidate(c.product_key)}
                  className="w-full border border-surface-700 px-3 py-2 font-mono text-xs hover:border-cyan-glow disabled:opacity-50 text-left flex flex-wrap gap-x-3 gap-y-0.5"
                >
                  <span className="text-foreground break-words min-w-0">{c.title}</span>
                  <span className="text-cyan-glow">{c.price ? `${c.price} €` : "sin precio"}</span>
                  {c.colour && <span className="text-muted-foreground">{c.colour}</span>}
                  {c.condition && <span className="text-muted-foreground">{c.condition}</span>}
                  {c.ean && <span className="text-muted-foreground">EAN {c.ean}</span>}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {(result.status === "no_match" || result.status === "ambiguous") && (
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            aria-label="EAN"
            placeholder="EAN / GTIN"
            inputMode="numeric"
            value={ean}
            onChange={(e) => setEan(e.target.value.replace(/\D/g, "").slice(0, 14))}
            className={inputCls + " sm:flex-1"}
          />
          <input
            aria-label="SKU"
            placeholder="SKU de la tienda"
            value={sku}
            onChange={(e) => setSku(e.target.value.slice(0, 64))}
            className={inputCls + " sm:flex-1"}
          />
          <button
            type="button"
            disabled={busy || (!ean && !sku)}
            onClick={() => onSearchIds({ ean: ean || undefined, sku: sku || undefined })}
            className="border border-cyan-glow/50 text-cyan-glow font-mono text-xs px-3 py-2 disabled:opacity-50 whitespace-nowrap"
          >
            {busy ? <Loader2 className="size-4 animate-spin inline" /> : "BUSCAR POR ID"}
          </button>
        </div>
      )}

      {conflicts.length > 0 && (
        <div className="border border-amber-500/50 p-2 space-y-1">
          <p className="font-mono text-[11px] text-amber-700 dark:text-yellow-400">
            Campos editados a mano que la importación no ha cambiado:
          </p>
          {conflicts.map((c) => (
            <div key={c.field} className="font-mono text-[11px] flex flex-wrap items-center gap-2">
              <span className="text-muted-foreground">{IMPORT_FIELD_LABELS[c.field]}:</span>
              <span className="break-all">«{c.current.slice(0, 80)}»</span>→
              <span className="break-all text-cyan-glow">«{c.imported.slice(0, 80)}»</span>
              <button
                type="button"
                onClick={() => onResolveConflict(c)}
                className="border border-surface-700 px-2 py-0.5 hover:border-cyan-glow"
              >
                USAR IMPORTADO
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
