import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState, useRef } from "react";
import {
  dealsService,
  isDuplicateDealError,
  type DealDetailData,
  type DealCreatePayload,
  type DealUpdatePayload,
} from "@/services/api/deals";
import { apiClient } from "@/services/api/client";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { categoriesService, type Category } from "@/services/api/categories";
import { storesService, type Store } from "@/services/api/stores";
import { productsApi, type AmazonPreviewResponse } from "@/services/api/products";
import {
  formatPrice,
  formatRelativeTime,
  slugify,
  calculateDiscount,
  toDatetimeLocal,
} from "@/lib/format";
import { errorMessage } from "@/lib/errors";
import { DEAL_STATUS_OPTIONS } from "@/lib/constants";
import { dealFormSchema } from "@/lib/validation/deals";
import { Plus, Trash2, Edit3, Upload, X, GripVertical, Wand2, Send, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/hooks/useAuth";
import { TelegramPanel } from "@/features/telegram/components/TelegramPanel";
import type { TelegramGenerateRequest } from "@/services/api/telegram";

export const Route = createFileRoute("/admin/chollos")({
  validateSearch: (search: Record<string, unknown>) => ({
    edit: typeof search.edit === "string" ? search.edit : undefined,
  }),
  component: AdminDeals,
});

type DealStatus = "active" | "expired" | "scheduled" | "draft";

/** Estado del formulario de admin. Los precios viven como string mientras el
 *  usuario edita (los <input type="number"> trabajan con string). */
interface DealForm {
  title: string;
  short_description: string;
  description: string;
  image_url: string;
  images: string[];
  current_price: string;
  previous_price: string;
  shipping_info: string;
  affiliate_url: string;
  store_id: string;
  category_id: string;
  subcategory_id: string;
  brand: string;
  status: DealStatus;
  expires_at: string; // datetime-local sin zona
  scheduled_for: string; // datetime-local sin zona
  external_id: string;
  show_keepa_chart: boolean;
  telegram_text?: string;
}

type TelegramPanelData = TelegramGenerateRequest & {
  images?: string[];
  image_url?: string | null;
};

function emptyForm(): DealForm {
  return {
    title: "",
    short_description: "",
    description: "",
    image_url: "",
    images: [],
    current_price: "",
    previous_price: "",
    shipping_info: "",
    affiliate_url: "",
    store_id: "",
    category_id: "",
    subcategory_id: "",
    brand: "",
    status: "active",
    expires_at: "",
    scheduled_for: "",
    external_id: "",
    show_keepa_chart: false,
  };
}

function dealToForm(d: DealDetailData): DealForm {
  return {
    title: d.title,
    short_description: d.short_description ?? "",
    description: d.description ?? "",
    image_url: d.image_url ?? "",
    images: d.images ?? [],
    current_price: String(d.current_price),
    previous_price: d.previous_price != null ? String(d.previous_price) : "",
    shipping_info: d.shipping_info ?? "",
    affiliate_url: d.affiliate_url ?? "",
    store_id: d.store_id ?? "",
    category_id: d.category_id ?? "",
    subcategory_id: d.subcategory_id ?? "",
    brand: d.brand ?? "",
    status: (d.status as DealStatus) || "active",
    expires_at: toDatetimeLocal(d.expires_at),
    scheduled_for: toDatetimeLocal(d.scheduled_for),
    external_id: d.external_id ?? "",
    show_keepa_chart: d.show_keepa_chart ?? false,
  };
}

function AdminDeals() {
  const { user } = useAuth();
  const [deals, setDeals] = useState<DealDetailData[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [cats, setCats] = useState<Category[]>([]);
  const [subcats, setSubcats] = useState<Category[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<DealDetailData | null>(null);
  const [form, setForm] = useState<DealForm>(emptyForm);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [uploading, setUploading] = useState(false);
  const [amazonUrl, setAmazonUrl] = useState("");
  const [autofilling, setAutofilling] = useState(false);
  const [showTelegramPanel, setShowTelegramPanel] = useState(false);
  const [telegramDealData, setTelegramDealData] = useState<TelegramPanelData | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const nav = useNavigate();

  /** Diálogo de conflicto cuando el backend devuelve 409 DUPLICATE_DEAL.
   *  Guardamos también el payload original para poder reintentar como
   *  UPDATE sobre el deal existente si el admin elige "Sobrescribir". */
  const [duplicateConflict, setDuplicateConflict] = useState<{
    existing_deal: { id: string; slug: string; title: string };
    pendingPayload: DealCreatePayload;
  } | null>(null);

  const load = () => {
    dealsService
      .getAdminAll(statusFilter)
      .then(setDeals)
      .catch((err: unknown) => toast.error(errorMessage(err)));
  };
  useEffect(() => {
    load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */
  }, [statusFilter]);

  useEffect(() => {
    Promise.all([storesService.getAll(), categoriesService.getAll()])
      .then(([s, c]) => {
        setStores(s);
        setCats(c.filter((x) => !x.parent_id));
        setSubcats(c.filter((x) => !!x.parent_id));
      })
      .catch((err: unknown) => toast.error(errorMessage(err)));
  }, []);

  const { edit: editId } = Route.useSearch();
  useEffect(() => {
    if (!editId || deals.length === 0 || showForm) return;
    const target = deals.find((d) => d.id === editId);
    if (target) startEdit(target);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deals, editId]);

  const startNew = () => {
    setEditing(null);
    setForm(emptyForm());
    setShowForm(true);
  };
  const startEdit = (d: DealDetailData) => {
    setEditing(d);
    setForm(dealToForm(d));
    setShowForm(true);
  };

  const autofillFromAmazon = async () => {
    const url = amazonUrl.trim();
    if (!url) {
      toast.error("Introduce una URL");
      return;
    }
    if (!/amazon\./i.test(url) && !/amzn\./i.test(url)) {
      toast.error("La URL no parece de Amazon");
      return;
    }
    setAutofilling(true);
    try {
      const d: AmazonPreviewResponse = await productsApi.previewFromUrl(url);
      const amazonStore = stores.find((s) => s.name.toLowerCase().includes("amazon"));

      setForm((f) => ({
        ...f,
        title: d.title || f.title,
        short_description: d.short_description || f.short_description,
        description: d.long_description || f.description,
        image_url: d.image_url || f.image_url,
        images: d.images.length > 0 ? d.images : d.image_url ? [d.image_url] : f.images,
        brand: d.brand || f.brand,
        current_price: d.current_price ? String(d.current_price) : f.current_price,
        previous_price: d.original_price ? String(d.original_price) : f.previous_price,
        affiliate_url: url,
        store_id: amazonStore?.id ?? f.store_id,
        category_id: d.category_id ?? f.category_id,
        subcategory_id: d.subcategory_id ?? f.subcategory_id,
        expires_at: d.expires_at ? toDatetimeLocal(d.expires_at) : f.expires_at,
        telegram_text: d.telegram_text || f.telegram_text,
        external_id: d.asin || f.external_id,
        show_keepa_chart: !!d.asin || f.show_keepa_chart,
      }));

      if (!showForm) {
        setEditing(null);
        setShowForm(true);
      }
      toast.success("Datos importados desde tu NAS");

      const allImages = d.images.length > 0 ? d.images : d.image_url ? [d.image_url] : [];
      openTelegramPanelWith({
        title: d.title || "",
        current_price: d.current_price || 0,
        previous_price: d.original_price || null,
        discount_percentage: d.discount_percentage || null,
        description: d.telegram_text || d.short_description || null,
        affiliate_url: url,
        expires_at: d.expires_at,
        images: allImages,
        image_url: allImages[0] ?? null,
      });
    } catch (e: unknown) {
      toast.error("Error desde el NAS: " + errorMessage(e));
    } finally {
      setAutofilling(false);
    }
  };

  /** Abre el panel Telegram con datos ya normalizados. */
  const openTelegramPanelWith = (data: TelegramPanelData) => {
    setTelegramDealData(data);
    setShowTelegramPanel(true);
  };

  /** Abre el panel a partir del formulario actual. */
  const openTelegramPanelFromForm = () => {
    const allImages = form.images.filter(Boolean);
    if (form.image_url && !allImages.includes(form.image_url)) allImages.unshift(form.image_url);
    const current = parseFloat(form.current_price) || 0;
    const previous = form.previous_price ? parseFloat(form.previous_price) : null;
    openTelegramPanelWith({
      title: form.title,
      current_price: current,
      previous_price: previous,
      discount_percentage: calculateDiscount(current, previous),
      description: form.telegram_text || form.short_description || null,
      affiliate_url: form.affiliate_url,
      expires_at: form.expires_at ? new Date(form.expires_at).toISOString() : null,
      images: allImages,
      image_url: allImages[0] ?? null,
    });
  };

  /** Abre el panel a partir de un deal ya guardado. */
  const openTelegramPanelFromDeal = (d: DealDetailData) => {
    const allImages = (d.images ?? []).filter(Boolean);
    if (d.image_url && !allImages.includes(d.image_url)) allImages.unshift(d.image_url);
    openTelegramPanelWith({
      title: d.title,
      current_price: d.current_price,
      previous_price: d.previous_price,
      discount_percentage: d.discount_percentage,
      description: d.short_description || null,
      affiliate_url: d.affiliate_url ?? "",
      expires_at: d.expires_at,
      images: allImages,
      image_url: allImages[0] ?? null,
    });
  };

  const buildPayload = (): DealCreatePayload => {
    const allImages = form.images.filter(Boolean);
    if (form.image_url && !allImages.includes(form.image_url)) allImages.unshift(form.image_url);
    const mainImage = allImages[0] ?? null;
    const current = +form.current_price;
    const previous = form.previous_price ? +form.previous_price : null;

    const payload: DealCreatePayload = {
      title: form.title.slice(0, 200),
      slug: editing?.slug ?? slugify(form.title) + "-" + Date.now().toString(36),
      short_description: form.short_description?.slice(0, 300) || null,
      description: form.description || null,
      image_url: mainImage,
      images: allImages,
      current_price: current,
      previous_price: previous,
      discount_percentage: calculateDiscount(current, previous),
      shipping_info: form.shipping_info || null,
      affiliate_url: form.affiliate_url,
      store_id: form.store_id || null,
      category_id: form.category_id || null,
      subcategory_id: form.subcategory_id || null,
      brand: form.brand || null,
      status: form.status,
      expires_at: form.expires_at ? new Date(form.expires_at).toISOString() : null,
      scheduled_for:
        form.status === "scheduled" && form.scheduled_for
          ? new Date(form.scheduled_for).toISOString()
          : null,
      external_id: form.external_id || null,
      show_keepa_chart: form.show_keepa_chart,
    };
    if (form.status === "active" && !editing) {
      payload.published_at = new Date().toISOString();
    }
    return payload;
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;

    const parsed = dealFormSchema.safeParse({
      title: form.title,
      affiliate_url: form.affiliate_url,
      current_price: form.current_price,
      previous_price: form.previous_price,
      short_description: form.short_description,
      description: form.description,
    });
    if (!parsed.success) {
      toast.error(parsed.error.issues[0]?.message ?? "Datos inválidos");
      return;
    }

    const payload = buildPayload();
    try {
      if (editing) {
        const update: DealUpdatePayload = { ...payload };
        await dealsService.update(editing.id, update);
        toast.success("Chollo actualizado");
      } else {
        await dealsService.create({ ...payload, source: "manual" });
        toast.success("Chollo creado");
      }
      setShowForm(false);
      load();
    } catch (e: unknown) {
      // El backend devuelve 409 DUPLICATE_DEAL cuando otro chollo ya tiene
      // este external_id (ASIN). Para CREATE abrimos el diálogo con las
      // opciones de sobrescribir / ir a editar / cancelar.
      // Para UPDATE mostramos un toast normal: el admin ya está editando un
      // deal concreto y el conflicto es raro (sólo si cambia el ASIN).
      if (!editing && isDuplicateDealError(e)) {
        setDuplicateConflict({
          existing_deal: e.data.existing_deal,
          pendingPayload: payload,
        });
        return;
      }
      toast.error(errorMessage(e));
    }
  };

  /** "Sobrescribir el existente": aplica los datos del form actual sobre el
   *  deal que ya tiene ese ASIN. Conserva id, slug, comentarios, votos y
   *  favoritos del registro original. */
  const overwriteExisting = async () => {
    if (!duplicateConflict) return;
    try {
      await dealsService.update(
        duplicateConflict.existing_deal.id,
        duplicateConflict.pendingPayload,
      );
      toast.success("Chollo sobrescrito");
      setDuplicateConflict(null);
      setShowForm(false);
      load();
    } catch (e: unknown) {
      toast.error(errorMessage(e));
    }
  };

  /** "Ir al chollo existente": navega a la página pública del chollo, que
   *  ya muestra un botón EDITAR para admins desde donde acceder al form
   *  con todos los datos cargados. Mejor UX que saltar directo al admin:
   *  el admin ve primero cómo está publicado y decide si entrar a editar. */
  const goEditExisting = () => {
    if (!duplicateConflict) return;
    const slug = duplicateConflict.existing_deal.slug;
    setDuplicateConflict(null);
    setShowForm(false);
    nav({ to: "/chollo/$slug", params: { slug } });
  };

  /** ONE-SHOT: recupera el ASIN de los chollos antiguos cuyo external_id es
   *  NULL. Para amzn.to acortados, sigue el redirect y extrae el ASIN. */
  const [backfilling, setBackfilling] = useState(false);
  const runBackfillAsins = async () => {
    if (
      !confirm(
        "¿Recuperar ASINs de los chollos antiguos? Puede tardar ~20s. Sólo deberías ejecutarlo una vez.",
      )
    )
      return;
    setBackfilling(true);
    try {
      const res = await apiClient.post<{
        processed: number;
        updated: number;
        failed: { id: string; title: string; reason: string }[];
      }>("/deals/admin/backfill-external-ids", {});
      const msg = `Procesados ${res.processed}, actualizados ${res.updated}, fallidos ${res.failed.length}`;
      if (res.failed.length === 0) toast.success(msg);
      else toast.warning(msg + " — revisa consola para detalle");
      // eslint-disable-next-line no-console
      console.table(res.failed);
      load();
    } catch (e: unknown) {
      toast.error(errorMessage(e));
    } finally {
      setBackfilling(false);
    }
  };

  const remove = async (id: string) => {
    if (!confirm("¿Eliminar este chollo?")) return;
    try {
      await dealsService.delete(id);
      load();
    } catch (e: unknown) {
      toast.error(errorMessage(e));
    }
  };

  const addImageUrl = () => {
    const url = form.image_url.trim();
    if (!url) return;
    if (form.images.includes(url)) {
      setForm({ ...form, image_url: "" });
      return;
    }
    setForm({ ...form, images: [...form.images, url], image_url: "" });
  };

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    const newUrls: string[] = [];
    const { supabase } = await import("@/integrations/supabase/client");
    for (const file of Array.from(files)) {
      if (!file.type.startsWith("image/")) {
        toast.error(`${file.name}: no es imagen`);
        continue;
      }
      if (file.size > 5 * 1024 * 1024) {
        toast.error(`${file.name}: máx 5MB`);
        continue;
      }
      const ext = file.name.split(".").pop();
      const path = `${user!.id}/${Date.now()}-${Math.random().toString(36).slice(2, 8)}.${ext}`;
      const { error } = await supabase.storage.from("deal-images").upload(path, file);
      if (error) {
        toast.error(error.message);
        continue;
      }
      const {
        data: { publicUrl },
      } = supabase.storage.from("deal-images").getPublicUrl(path);
      newUrls.push(publicUrl);
    }
    setForm((f) => ({ ...f, images: [...f.images, ...newUrls] }));
    setUploading(false);
    if (fileRef.current) fileRef.current.value = "";
    if (newUrls.length) toast.success(`${newUrls.length} imagen(es) subida(s)`);
  };

  const removeImage = (i: number) => {
    setForm({ ...form, images: form.images.filter((_, idx) => idx !== i) });
  };

  const moveImage = (i: number, dir: -1 | 1) => {
    const j = i + dir;
    if (j < 0 || j >= form.images.length) return;
    const arr = [...form.images];
    const a = arr[i];
    const b = arr[j];
    if (a === undefined || b === undefined) return; // guards para noUncheckedIndexedAccess
    arr[i] = b;
    arr[j] = a;
    setForm({ ...form, images: arr });
  };

  const filteredSubcats = subcats.filter((s) => s.parent_id === form.category_id);
  const inputCls =
    "w-full bg-surface-900 border border-surface-700 px-3 py-2 font-mono text-sm outline-none focus:border-cyan-glow";

  return (
    <div>
      {showTelegramPanel && telegramDealData && (
        <TelegramPanel dealData={telegramDealData} onClose={() => setShowTelegramPanel(false)} />
      )}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <h2 className="font-mono text-sm uppercase text-cyan-glow">Gestión de chollos</h2>
        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-surface-900 border border-surface-700 px-3 py-2 font-mono text-xs uppercase outline-none focus:border-cyan-glow"
          >
            {DEAL_STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <button
            onClick={runBackfillAsins}
            disabled={backfilling}
            className="border border-amber-500/50 text-amber-400 font-mono text-xs font-bold px-3 py-2 flex items-center gap-2 hover:border-amber-400 hover:bg-amber-400/10 disabled:opacity-50 disabled:cursor-wait"
            title="One-shot: rellena external_id (ASIN) de chollos antiguos"
          >
            {backfilling ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Wand2 className="size-4" />
            )}
            BACKFILL ASIN
          </button>
          <button
            onClick={startNew}
            className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2 flex items-center gap-2 hover:bg-foreground"
          >
            <Plus className="size-4" /> NUEVO
          </button>
        </div>
      </div>

      {/* AUTOCOMPLETAR DESDE AMAZON */}
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
            value={amazonUrl}
            onChange={(e) => setAmazonUrl(e.target.value)}
            className={inputCls + " flex-1"}
          />
          <button
            type="button"
            onClick={autofillFromAmazon}
            disabled={autofilling}
            className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2 flex items-center justify-center gap-2 hover:bg-foreground disabled:opacity-50"
          >
            {autofilling ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Wand2 className="size-4" />
            )}
            {autofilling ? "PROCESANDO..." : "[ AUTOCOMPLETAR ]"}
          </button>
        </div>
      </div>

      {showForm && (
        <form
          onSubmit={save}
          className="bg-surface-800 border border-surface-700 p-5 mb-6 space-y-3"
        >
          <h3 className="font-mono text-xs uppercase text-cyan-glow">
            {editing ? "Editar chollo" : "Nuevo chollo"}
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
                [ AÑADIR URL ]
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
                <Upload className="size-3" /> {uploading ? "SUBIENDO..." : "[ SUBIR ARCHIVOS ]"}
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
              value={form.category_id}
              onChange={(e) =>
                setForm({ ...form, category_id: e.target.value, subcategory_id: "" })
              }
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
            onClick={openTelegramPanelFromForm}
            className="w-full border border-cyan-glow/50 text-cyan-glow font-mono text-xs py-2 flex items-center justify-center gap-2 hover:bg-cyan-glow/10"
          >
            <Send className="size-3.5" /> 🚀 Publicar en Telegram
          </button>

          <div className="flex gap-2">
            <button
              type="submit"
              className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2"
            >
              [ GUARDAR ]
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="border border-surface-700 font-mono text-xs px-4 py-2"
            >
              [ CANCELAR ]
            </button>
          </div>
        </form>
      )}

      <div className="bg-surface-800 border border-surface-700 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-surface-700 font-mono text-xs uppercase text-muted-foreground">
            <tr>
              <th className="p-3 w-14">
                <span className="sr-only">Imagen</span>
              </th>
              <th className="text-left p-3">Título</th>
              <th className="text-left p-3">Tienda</th>
              <th className="text-right p-3">Precio</th>
              <th className="text-left p-3">Estado</th>
              <th className="text-left p-3">Fecha</th>
              <th className="p-3">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {deals.map((d) => {
              const stCls =
                d.status === "active"
                  ? "bg-cyan-glow/15 text-cyan-glow"
                  : d.status === "scheduled"
                    ? "bg-amber-500/15 text-amber-400"
                    : d.status === "expired"
                      ? "bg-alert-red/15 text-alert-red"
                      : "bg-surface-700 text-muted-foreground";
              return (
                <tr key={d.id} className="border-b border-surface-700/50 hover:bg-surface-700/30">
                  <td className="p-2">
                    {d.image_url || (d.images && d.images[0]) ? (
                      <img
                        src={d.images?.[0] ?? d.image_url ?? ""}
                        alt=""
                        className="w-10 h-10 object-contain bg-white rounded-sm shrink-0"
                      />
                    ) : (
                      <div className="w-10 h-10 bg-surface-700 rounded-sm" />
                    )}
                  </td>
                  <td className="p-3">
                    <Link
                      to="/chollo/$slug"
                      params={{ slug: d.slug }}
                      className="hover:text-cyan-glow"
                    >
                      {d.title}
                    </Link>
                  </td>
                  <td className="p-3 text-muted-foreground font-mono text-xs">
                    {d.store?.name ?? "—"}
                  </td>
                  <td className="p-3 text-right font-mono text-cyan-glow">
                    {formatPrice(d.current_price)}
                  </td>
                  <td className="p-3">
                    <span className={`font-mono text-[10px] uppercase px-2 py-1 ${stCls}`}>
                      {d.status}
                    </span>
                  </td>
                  <td className="p-3 text-muted-foreground font-mono text-xs">
                    {d.status === "scheduled" && d.scheduled_for ? (
                      <>📅 {new Date(d.scheduled_for).toLocaleString("es-ES")}</>
                    ) : d.expires_at ? (
                      <>⏱ {new Date(d.expires_at).toLocaleString("es-ES")}</>
                    ) : (
                      formatRelativeTime(d.created_at ?? d.published_at ?? "")
                    )}
                  </td>
                  <td className="p-3 flex gap-1">
                    <button
                      type="button"
                      onClick={() => startEdit(d)}
                      className="p-1.5 hover:text-cyan-glow"
                      title="Editar"
                    >
                      <Edit3 className="size-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => openTelegramPanelFromDeal(d)}
                      className="p-1.5 hover:text-cyan-glow"
                      title="Publicar en Telegram"
                    >
                      <Send className="size-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => remove(d.id)}
                      className="p-1.5 hover:text-alert-red"
                      title="Eliminar"
                    >
                      <Trash2 className="size-4" />
                    </button>
                  </td>
                </tr>
              );
            })}
            {deals.length === 0 && (
              <tr>
                <td colSpan={7} className="p-6 text-center text-muted-foreground font-mono text-xs">
                  SIN_RESULTADOS
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <AlertDialog
        open={!!duplicateConflict}
        onOpenChange={(open) => {
          if (!open) setDuplicateConflict(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Chollo duplicado</AlertDialogTitle>
            <AlertDialogDescription>
              Ya existe el chollo «{duplicateConflict?.existing_deal.title}» con este ASIN. ¿Qué
              quieres hacer?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="flex flex-col gap-2 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={() => setDuplicateConflict(null)}
              className="px-4 py-2 font-mono text-xs uppercase border border-surface-600 hover:border-foreground transition-colors"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={goEditExisting}
              className="px-4 py-2 font-mono text-xs uppercase border border-cyan-glow text-cyan-glow hover:bg-cyan-glow hover:text-surface-900 transition-colors"
            >
              Ir al chollo existente
            </button>
            <button
              type="button"
              onClick={overwriteExisting}
              className="px-4 py-2 font-mono text-xs uppercase bg-alert-red text-white hover:opacity-90 transition-opacity"
            >
              Sobrescribir el existente
            </button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
