/** Bloque del formulario para chollos de Awin / Tradedoubler: significado y
 *  evidencia del precio anterior, comprobación manual en tienda y estado de
 *  publicación calculado por el backend (única fuente de las reglas). */
import { useEffect, useState, type Dispatch, type SetStateAction } from "react";
import { CheckCircle2, ShieldAlert } from "lucide-react";
import { affiliatesApi, type ReadinessResponse } from "@/services/api/affiliates";
import { adminInputCls as inputCls, REFERENCE_TYPE_LABELS, type DealForm } from "../deal-form";

interface Props {
  readonly form: DealForm;
  readonly setForm: Dispatch<SetStateAction<DealForm>>;
  readonly onReadiness: (readiness: ReadinessResponse | null) => void;
}

export function NetworkDealSection({ form, setForm, onReadiness }: Props) {
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);

  useEffect(() => {
    const handle = setTimeout(() => {
      const images = form.images.filter(Boolean);
      affiliatesApi
        .readiness({
          affiliate_program_id: form.affiliate_program_id || null,
          data_source: form.data_source || null,
          affiliate_url: form.affiliate_url || null,
          title: form.title || null,
          current_price: form.current_price ? Number(form.current_price) : null,
          previous_price: form.previous_price ? Number(form.previous_price) : null,
          price_reference_type: form.price_reference_type || null,
          price_reference_evidence: form.price_reference_evidence || null,
          shipping_info: form.shipping_info || null,
          short_description: form.short_description || null,
          category_id: form.category_id || null,
          image_url: images[0] ?? (form.image_url || null),
          data_provider_updated_at: form.data_provider_updated_at || null,
          price_verified_at: form.price_verified_at || null,
        })
        .then((r) => {
          setReadiness(r);
          onReadiness(r);
        })
        .catch(() => {
          setReadiness(null);
          onReadiness(null);
        });
    }, 400);
    return () => clearTimeout(handle);
  }, [form, onReadiness]);

  const verified = !!form.price_verified_at;

  return (
    <fieldset className="border border-surface-700 p-3 space-y-3">
      <legend className="font-mono text-xs uppercase text-cyan-glow px-1">
        Afiliación y precio de referencia
      </legend>
      <div className="grid sm:grid-cols-2 gap-3">
        <label className="block">
          <span className="font-mono text-[10px] uppercase text-muted-foreground block mb-1">
            ¿Qué es el precio anterior?
          </span>
          <select
            aria-label="Tipo de precio anterior"
            value={form.price_reference_type || "none"}
            onChange={(e) => setForm({ ...form, price_reference_type: e.target.value })}
            className={inputCls}
          >
            {Object.entries(REFERENCE_TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="font-mono text-[10px] uppercase text-muted-foreground block mb-1">
            Evidencia (dónde y cuándo se comprobó)
          </span>
          <input
            aria-label="Evidencia del precio anterior"
            maxLength={500}
            placeholder="p. ej. Tachado en la ficha de la tienda el 08/11 10:15"
            value={form.price_reference_evidence}
            onChange={(e) => setForm({ ...form, price_reference_evidence: e.target.value })}
            className={inputCls}
          />
        </label>
      </div>
      <label className="flex items-start gap-2 font-mono text-xs cursor-pointer select-none">
        <input
          type="checkbox"
          checked={verified}
          onChange={(e) =>
            setForm({
              ...form,
              price_verified_at: e.target.checked ? new Date().toISOString() : "",
            })
          }
          className="accent-cyan-500 mt-0.5"
        />
        <span>
          He comprobado ahora en la tienda el precio, el envío y la disponibilidad
          {verified && (
            <span className="text-muted-foreground">
              {" "}
              (
              {new Date(form.price_verified_at).toLocaleString("es-ES", {
                timeStyle: "short",
                dateStyle: "short",
              })}
              )
            </span>
          )}
        </span>
      </label>
      <p className="font-mono text-[10px] text-muted-foreground">
        Fuente: {form.data_source || "—"} · dato del proveedor:{" "}
        {form.data_provider_updated_at
          ? new Date(form.data_provider_updated_at).toLocaleString("es-ES", {
              dateStyle: "short",
              timeStyle: "short",
            })
          : "fecha desconocida"}
      </p>
      {readiness?.applies &&
        (readiness.ready ? (
          <p className="font-mono text-xs text-cyan-glow flex items-center gap-1.5">
            <CheckCircle2 className="size-4" /> Lista para publicar
            {readiness.savings_amount &&
              ` · ahorro ${readiness.savings_amount.replace(".", ",")} € (-${readiness.discount_percentage} %)`}
          </p>
        ) : (
          <div className="space-y-1" role="status">
            <p className="font-mono text-xs text-alert-red flex items-center gap-1.5">
              <ShieldAlert className="size-4" /> Solo se puede guardar como borrador:
            </p>
            <ul className="list-disc pl-5 font-mono text-[11px] text-muted-foreground space-y-0.5">
              {readiness.blockers.map((b) => (
                <li key={b.code}>{b.message}</li>
              ))}
            </ul>
          </div>
        ))}
    </fieldset>
  );
}
