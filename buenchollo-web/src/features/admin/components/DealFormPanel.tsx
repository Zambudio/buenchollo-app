/** Formulario de creación/edición de chollos del admin (TD-03).
 *  Presentación: el estado y las operaciones llegan por props desde la ruta. */
import type { Dispatch, SetStateAction } from "react";
import { GripVertical, Send, Upload, X } from "lucide-react";
import type { Category } from "@/services/api/categories";
import type { Store } from "@/services/api/stores";
import { adminInputCls as inputCls, type DealForm, type DealStatus } from "../deal-form";
import type { useDealImages } from "../hooks/useDealImages";

interface Props {
  readonly form: DealForm;
  readonly setForm: Dispatch<SetStateAction<DealForm>>;
  readonly isEditing: boolean;
  readonly stores: Store[];
  readonly cats: Category[];
  readonly subcats: Category[];
  readonly images: ReturnType<typeof useDealImages>;
  readonly onSubmit: (e: React.FormEvent) => void;
  readonly onCancel: () => void;
  readonly onOpenTelegram: () => void;
}

export function DealFormPanel({
  form,
  setForm,
  isEditing,
  stores,
  cats,
  subcats,
  images,
  onSubmit,
  onCancel,
  onOpenTelegram,
}: Props) {
  const { uploading, fileRef, addImageUrl, handleFiles, removeImage, moveImage } = images;
  const filteredSubcats = subcats.filter((s) => s.parent_id === form.category_id);

  return (
    <form
      onSubmit={onSubmit}
      className="bg-surface-800 border border-surface-700 p-5 mb-6 space-y-3"
    >
      <h3 className="font-mono text-xs uppercase text-cyan-glow">
        {isEditing ? "Editar chollo" : "Nuevo chollo"}
      </h3>
      <input
        placeholder="Título *"
        required
        value={form.title}
        onChange={(e) => setForm({ ...form, title: e.target.value })}
        className={inputCls}
      />
      <input
        placeholder="Descripción corta"
        value={form.short_description}
        onChange={(e) => setForm({ ...form, short_description: e.target.value })}
        className={inputCls}
      />
      <textarea
        placeholder="Descripción larga"
        value={form.description}
        onChange={(e) => setForm({ ...form, description: e.target.value })}
        rows={3}
        className={inputCls}
      />

      {/* IMÁGENES */}
      <div className="border border-surface-700 p-3 space-y-3">
        <div className="flex items-center justify-between">
          <span className="font-mono text-xs uppercase text-cyan-glow">
            Imágenes ({form.images.length})
          </span>
          <span className="font-mono text-[10px] text-muted-foreground">
            La primera es la principal
          </span>
        </div>
        <div className="flex gap-2">
          <input
            placeholder="Añadir por URL..."
            value={form.image_url}
            onChange={(e) => setForm({ ...form, image_url: e.target.value })}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addImageUrl();
              }
            }}
            className={inputCls + " flex-1"}
          />
          <button
            type="button"
            onClick={addImageUrl}
            className="border border-surface-700 px-3 font-mono text-xs hover:border-cyan-glow"
          >
            AÑADIR URL
          </button>
        </div>
        <div className="flex items-center gap-2">
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            multiple
            onChange={(e) => handleFiles(e.target.files)}
            className="hidden"
          />
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="border border-surface-700 px-3 py-2 font-mono text-xs hover:border-cyan-glow flex items-center gap-2 disabled:opacity-50"
          >
            <Upload className="size-3" /> {uploading ? "SUBIENDO..." : "SUBIR ARCHIVOS"}
          </button>
          <span className="font-mono text-[10px] text-muted-foreground">
            JPG/PNG/WEBP · máx 5MB
          </span>
        </div>
        {form.images.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2">
            {form.images.map((url, i) => (
              <div
                key={i}
                className="relative group bg-surface-900 border border-surface-700 aspect-square overflow-hidden"
              >
                <img src={url} alt="" className="w-full h-full object-cover" />
                {i === 0 && (
                  <span className="absolute top-1 left-1 bg-cyan-glow text-surface-900 font-mono text-[9px] font-bold px-1">
                    PRINCIPAL
                  </span>
                )}
                <div className="absolute inset-0 bg-surface-900/80 opacity-0 group-hover:opacity-100 transition flex items-center justify-center gap-1">
                  <button
                    type="button"
                    onClick={() => moveImage(i, -1)}
                    disabled={i === 0}
                    className="p-1 hover:text-cyan-glow disabled:opacity-30"
                  >
                    <GripVertical className="size-3 rotate-90" />
                  </button>
                  <button
                    type="button"
                    onClick={() => moveImage(i, 1)}
                    disabled={i === form.images.length - 1}
                    className="p-1 hover:text-cyan-glow disabled:opacity-30"
                  >
                    <GripVertical className="size-3 -rotate-90" />
                  </button>
                  <button
                    type="button"
                    onClick={() => removeImage(i)}
                    className="p-1 hover:text-alert-red"
                  >
                    <X className="size-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="grid sm:grid-cols-3 gap-3">
        <input
          type="number"
          step="0.01"
          placeholder="Precio actual *"
          required
          value={form.current_price}
          onChange={(e) => setForm({ ...form, current_price: e.target.value })}
          className={inputCls}
        />
        <input
          type="number"
          step="0.01"
          placeholder="Precio anterior"
          value={form.previous_price}
          onChange={(e) => setForm({ ...form, previous_price: e.target.value })}
          className={inputCls}
        />
        <input
          placeholder="Marca"
          value={form.brand}
          onChange={(e) => setForm({ ...form, brand: e.target.value })}
          className={inputCls}
        />
      </div>
      <input
        placeholder="Envío (texto)"
        value={form.shipping_info}
        onChange={(e) => setForm({ ...form, shipping_info: e.target.value })}
        className={inputCls}
      />
      <input
        placeholder="Enlace afiliado *"
        required
        value={form.affiliate_url}
        onChange={(e) => setForm({ ...form, affiliate_url: e.target.value })}
        className={inputCls}
      />
      <div className="grid sm:grid-cols-4 gap-3">
        <select
          aria-label="Tienda"
          value={form.store_id}
          onChange={(e) => setForm({ ...form, store_id: e.target.value })}
          className={inputCls}
        >
          <option value="">— Tienda —</option>
          {stores.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Categoría"
          value={form.category_id}
          onChange={(e) => setForm({ ...form, category_id: e.target.value, subcategory_id: "" })}
          className={inputCls}
        >
          <option value="">— Categoría —</option>
          {cats.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Subcategoría"
          value={form.subcategory_id}
          onChange={(e) => setForm({ ...form, subcategory_id: e.target.value })}
          className={inputCls}
          disabled={!form.category_id || filteredSubcats.length === 0}
        >
          <option value="">
            {form.category_id
              ? filteredSubcats.length
                ? "— Subcategoría —"
                : "Sin subcategorías"
              : "Elige categoría primero"}
          </option>
          {filteredSubcats.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Estado"
          value={form.status}
          onChange={(e) => setForm({ ...form, status: e.target.value as DealStatus })}
          className={inputCls}
        >
          <option value="active">Activo</option>
          <option value="expired">Caducado</option>
          <option value="scheduled">Programado</option>
          <option value="draft">Borrador</option>
        </select>
      </div>
      <div className="flex items-center gap-3 bg-surface-900 border border-surface-600 px-3 py-2.5">
        <input
          placeholder="ASIN de Amazon (para gráfica de precios)"
          value={form.external_id}
          onChange={(e) => setForm({ ...form, external_id: e.target.value })}
          className="flex-1 bg-transparent font-mono text-xs outline-none text-foreground placeholder:text-muted-foreground"
        />
        <label className="flex items-center gap-2 font-mono text-xs text-muted-foreground whitespace-nowrap cursor-pointer select-none shrink-0">
          <input
            type="checkbox"
            checked={form.show_keepa_chart}
            onChange={(e) => setForm({ ...form, show_keepa_chart: e.target.checked })}
            className="accent-cyan-500"
          />
          Mostrar gráfica Keepa
        </label>
      </div>

      <div className="grid sm:grid-cols-2 gap-3">
        <label className="block">
          <span className="font-mono text-[10px] uppercase text-muted-foreground block mb-1">
            Caduca el (opcional)
          </span>
          <input
            type="datetime-local"
            value={form.expires_at}
            onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
            className={inputCls}
          />
        </label>
        {form.status === "scheduled" && (
          <label className="block">
            <span className="font-mono text-[10px] uppercase text-cyan-glow block mb-1">
              Publicar el *
            </span>
            <input
              type="datetime-local"
              required
              value={form.scheduled_for}
              onChange={(e) => setForm({ ...form, scheduled_for: e.target.value })}
              className={inputCls}
            />
          </label>
        )}
      </div>
      {form.status === "draft" && (
        <p className="font-mono text-[10px] text-muted-foreground">
          📝 BORRADOR · No se publicará. Puedes previsualizarlo en su URL siendo admin.
        </p>
      )}
      {form.status === "expired" && (
        <p className="font-mono text-[10px] text-alert-red">
          ⛔ CADUCADO · Aparecerá en gris con aviso de oferta finalizada.
        </p>
      )}
      <button
        type="button"
        onClick={onOpenTelegram}
        className="w-full border border-cyan-glow/50 text-cyan-glow font-mono text-xs py-2 flex items-center justify-center gap-2 hover:bg-cyan-glow/10"
      >
        <Send className="size-3.5" /> 🚀 Publicar en Telegram
      </button>

      <div className="flex gap-2">
        <button
          type="submit"
          className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2"
        >
          GUARDAR
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="border border-surface-700 font-mono text-xs px-4 py-2"
        >
          CANCELAR
        </button>
      </div>
    </form>
  );
}
