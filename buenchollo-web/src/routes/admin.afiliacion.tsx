/** Registro de programas de afiliación (Awin / Tradedoubler) por tienda.
 *  Los IDs sembrados son referencias SIN verificar: nada se activa solo. */
import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { CheckCircle2, Loader2, RefreshCw, Save, XCircle } from "lucide-react";
import { errorMessage } from "@/lib/errors";
import {
  affiliatesApi,
  type AffiliateProgram,
  type AffiliateProgramUpdate,
  type IntegrationStatus,
} from "@/services/api/affiliates";
import { storesService, type Store } from "@/services/api/stores";

export const Route = createFileRoute("/admin/afiliacion")({ component: AdminAffiliates });

const inputCls =
  "bg-surface-900 border border-surface-700 px-3 py-2 font-mono text-sm outline-none focus:border-cyan-glow w-full";

const MEMBERSHIP_OPTIONS = ["unknown", "pending", "joined", "rejected", "suspended", "notjoined"];

function Flag({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={`flex items-center gap-1 font-mono text-[11px] ${ok ? "text-cyan-glow" : "text-alert-red"}`}
    >
      {ok ? <CheckCircle2 className="size-3.5" /> : <XCircle className="size-3.5" />} {label}
    </span>
  );
}

function AdminAffiliates() {
  const [programs, setPrograms] = useState<AffiliateProgram[]>([]);
  const [status, setStatus] = useState<IntegrationStatus | null>(null);
  const [stores, setStores] = useState<Store[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(() => {
    affiliatesApi
      .programs()
      .then(setPrograms)
      .catch((e: unknown) => toast.error(errorMessage(e)));
    affiliatesApi
      .status()
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);
  useEffect(() => {
    load();
    storesService
      .getAdminAll()
      .then(setStores)
      .catch(() => setStores([]));
  }, [load]);

  const refreshMembership = async () => {
    setBusy("membership");
    try {
      await affiliatesApi.refreshMembership();
      toast.success("Adhesión consultada a las redes");
      load();
    } catch (e: unknown) {
      toast.error(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };

  const syncFeeds = async (programId?: string) => {
    setBusy("sync");
    try {
      await affiliatesApi.syncFeeds(programId);
      toast.success("Sincronización lanzada en segundo plano. Recarga en unos minutos.");
    } catch (e: unknown) {
      toast.error(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-mono text-sm uppercase text-cyan-glow">
          Afiliación · Awin y Tradedoubler
        </h2>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={refreshMembership}
            disabled={!!busy}
            className="border border-cyan-glow/50 text-cyan-glow font-mono text-xs px-3 py-2 flex items-center gap-2 disabled:opacity-50"
          >
            {busy === "membership" ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <RefreshCw className="size-4" />
            )}
            COMPROBAR ADHESIÓN
          </button>
          <button
            type="button"
            onClick={() => syncFeeds()}
            disabled={!!busy}
            className="border border-surface-700 font-mono text-xs px-3 py-2 flex items-center gap-2 hover:border-cyan-glow disabled:opacity-50"
          >
            <RefreshCw className="size-4" /> SINCRONIZAR FEEDS AWIN
          </button>
        </div>
      </div>

      {status && (
        <div className="bg-surface-800 border border-surface-700 p-3 flex flex-wrap gap-x-4 gap-y-1">
          <Flag ok={status.awin_publisher_api} label="Awin Publisher API" />
          <Flag ok={status.awin_feeds} label="Awin feeds" />
          <Flag ok={status.tradedoubler_products} label="Tradedoubler Products" />
          <Flag ok={status.tradedoubler_site_id} label="Tradedoubler site ID" />
        </div>
      )}

      <p className="font-mono text-[11px] text-muted-foreground">
        Los programas sembrados son referencias sin verificar. Solo con adhesión «joined» se generan
        enlaces; publicar exige además permiso de imágenes, precio anterior con evidencia y datos
        recientes. Guía: docs/guides/AFFILIATE-NETWORKS.md.
      </p>

      {programs.map((p) => (
        <ProgramCard
          key={p.id}
          program={p}
          stores={stores}
          onSaved={load}
          onSync={() => syncFeeds(p.id)}
        />
      ))}
    </div>
  );
}

function ProgramCard({
  program,
  stores,
  onSaved,
  onSync,
}: {
  program: AffiliateProgram;
  stores: Store[];
  onSaved: () => void;
  onSync: () => void;
}) {
  const [draft, setDraft] = useState(() => toDraft(program));
  const [saving, setSaving] = useState(false);
  useEffect(() => setDraft(toDraft(program)), [program]);

  const save = async () => {
    setSaving(true);
    const update: AffiliateProgramUpdate = {
      enabled: draft.enabled,
      store_id: draft.store_id || null,
      domains: draft.domains
        .split(",")
        .map((d) => d.trim())
        .filter(Boolean),
      promo_spaces: draft.promo_spaces,
      selected_feed_ids: draft.selected_feed_ids,
      disclosure_text: draft.disclosure_text || null,
      max_data_age_hours: draft.max_data_age_hours,
      restrictions: {
        ...program.restrictions,
        image_channels: draft.image_channels,
        notes: draft.restriction_notes || null,
      },
      notes: draft.notes || null,
      ...(draft.membership_status !== program.membership_status
        ? { membership_status: draft.membership_status }
        : {}),
      ...(program.network === "tradedoubler" &&
      draft.deeplink_verified !== !!program.deeplink_verified_at
        ? { deeplink_verified: draft.deeplink_verified }
        : {}),
    };
    try {
      await affiliatesApi.updateProgram(program.id, update);
      toast.success(`${program.name} guardado`);
      onSaved();
    } catch (e: unknown) {
      toast.error(errorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  const toggle = (list: string[], value: string) =>
    list.includes(value) ? list.filter((v) => v !== value) : [...list, value];

  return (
    <section className="bg-surface-800 border border-surface-700 p-4 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-mono text-xs uppercase text-cyan-glow break-words">
          {program.name} · {program.network} · {program.advertiser_id}
        </h3>
        <label className="flex items-center gap-2 font-mono text-xs cursor-pointer">
          <input
            type="checkbox"
            checked={draft.enabled}
            onChange={(e) => setDraft({ ...draft, enabled: e.target.checked })}
            className="accent-cyan-500"
          />
          Habilitado
        </label>
      </div>
      <p className="font-mono text-[10px] text-muted-foreground">
        Adhesión: {program.membership_status} ·{" "}
        {program.membership_checked_at
          ? `comprobada ${new Date(program.membership_checked_at).toLocaleString("es-ES")} (${program.membership_source})`
          : "nunca comprobada"}
      </p>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        <label className="block">
          <span className="font-mono text-[10px] uppercase text-muted-foreground">
            Adhesión (manual)
          </span>
          <select
            value={draft.membership_status}
            onChange={(e) => setDraft({ ...draft, membership_status: e.target.value })}
            className={inputCls}
          >
            {MEMBERSHIP_OPTIONS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="font-mono text-[10px] uppercase text-muted-foreground">Tienda</span>
          <select
            value={draft.store_id}
            onChange={(e) => setDraft({ ...draft, store_id: e.target.value })}
            className={inputCls}
          >
            <option value="">— Sin tienda —</option>
            {stores.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="font-mono text-[10px] uppercase text-muted-foreground">
            Caducidad del dato (h)
          </span>
          <input
            type="number"
            min={1}
            max={336}
            value={draft.max_data_age_hours}
            onChange={(e) =>
              setDraft({ ...draft, max_data_age_hours: Number(e.target.value) || 24 })
            }
            className={inputCls}
          />
        </label>
      </div>

      <label className="block">
        <span className="font-mono text-[10px] uppercase text-muted-foreground">
          Dominios (separados por coma; admite ruta: samsung.com/es)
        </span>
        <input
          value={draft.domains}
          onChange={(e) => setDraft({ ...draft, domains: e.target.value })}
          className={inputCls}
        />
      </label>

      <div className="space-y-2 font-mono text-xs">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <span className="text-muted-foreground w-full sm:w-auto">
            Espacios promocionales autorizados:
          </span>
          {["web", "telegram"].map((space) => (
            <label key={space} className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={draft.promo_spaces.includes(space)}
                onChange={() =>
                  setDraft({ ...draft, promo_spaces: toggle(draft.promo_spaces, space) })
                }
                className="accent-cyan-500"
              />
              {space}
            </label>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <span className="text-muted-foreground w-full sm:w-auto">Imágenes permitidas en:</span>
          {["web", "telegram"].map((ch) => (
            <label key={ch} className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={draft.image_channels.includes(ch)}
                onChange={() =>
                  setDraft({ ...draft, image_channels: toggle(draft.image_channels, ch) })
                }
                className="accent-cyan-500"
              />
              {ch}
            </label>
          ))}
        </div>
        {program.network === "tradedoubler" && (
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={draft.deeplink_verified}
              onChange={(e) => setDraft({ ...draft, deeplink_verified: e.target.checked })}
              className="accent-cyan-500"
            />
            Deeplink verificado en mi cuenta TD
          </label>
        )}
      </div>

      <label className="block">
        <span className="font-mono text-[10px] uppercase text-muted-foreground">
          Aviso adicional del programa (post)
        </span>
        <input
          maxLength={300}
          value={draft.disclosure_text}
          onChange={(e) => setDraft({ ...draft, disclosure_text: e.target.value })}
          className={inputCls}
        />
      </label>
      <label className="block">
        <span className="font-mono text-[10px] uppercase text-muted-foreground">
          Restricciones (Marketplace, vendedores, imágenes, canales)
        </span>
        <textarea
          rows={2}
          maxLength={1000}
          value={draft.restriction_notes}
          onChange={(e) => setDraft({ ...draft, restriction_notes: e.target.value })}
          className={inputCls}
        />
      </label>
      {program.notes && (
        <p className="font-mono text-[10px] text-muted-foreground">{program.notes}</p>
      )}

      <div className="space-y-1">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="font-mono text-[10px] uppercase text-muted-foreground">
            Feeds ({program.feeds.length})
          </span>
          {program.network === "awin" && (
            <button
              type="button"
              onClick={onSync}
              className="border border-surface-700 px-2 py-1 font-mono text-[10px] hover:border-cyan-glow"
            >
              SINCRONIZAR ESTE PROGRAMA
            </button>
          )}
        </div>
        {program.feeds.length === 0 && (
          <p className="font-mono text-[10px] text-muted-foreground">
            Sin feeds descubiertos: comprueba adhesión (TD) o sincroniza la lista de feeds (Awin).
          </p>
        )}
        {program.feeds.map((f) => (
          <label
            key={f.feed_id}
            className="flex flex-wrap items-center gap-x-2 gap-y-0.5 font-mono text-[11px] cursor-pointer"
          >
            <input
              type="checkbox"
              checked={draft.selected_feed_ids.includes(f.feed_id)}
              onChange={() =>
                setDraft({
                  ...draft,
                  selected_feed_ids: toggle(draft.selected_feed_ids, f.feed_id),
                })
              }
              className="accent-cyan-500"
            />
            <span>
              {f.feed_id} · {f.name ?? "sin nombre"} {f.language ? `(${f.language})` : ""}
            </span>
            <span className="text-muted-foreground">
              {f.available === false ? "no disponible · " : ""}
              {f.products ? `${f.products} productos · ` : ""}
              {f.last_imported ? `actualizado ${f.last_imported}` : ""}
              {f.last_status
                ? ` · última sync: ${f.last_status}${f.rows != null ? ` (${f.rows} filas)` : ""}`
                : ""}
            </span>
            {f.last_error && <span className="text-alert-red break-words">{f.last_error}</span>}
          </label>
        ))}
      </div>

      <button
        type="button"
        onClick={save}
        disabled={saving}
        className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2 flex items-center gap-2 disabled:opacity-50"
      >
        {saving ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />} GUARDAR
      </button>
    </section>
  );
}

function toDraft(p: AffiliateProgram) {
  return {
    enabled: p.enabled,
    membership_status: p.membership_status,
    store_id: p.store_id ?? "",
    domains: p.domains.join(", "),
    promo_spaces: p.promo_spaces,
    image_channels: p.restrictions?.image_channels ?? [],
    restriction_notes: p.restrictions?.notes ?? "",
    disclosure_text: p.disclosure_text ?? "",
    max_data_age_hours: p.max_data_age_hours,
    selected_feed_ids: p.feeds.filter((f) => f.selected).map((f) => f.feed_id),
    deeplink_verified: !!p.deeplink_verified_at,
    notes: p.notes ?? "",
  };
}
