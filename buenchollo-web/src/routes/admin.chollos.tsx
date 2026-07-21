/** Ruta admin de gestión de chollos.
 *
 *  Orquesta las piezas de features/admin (TD-03): el listado y catálogos
 *  viven en useAdminDeals, las operaciones de imágenes en useDealImages,
 *  las transformaciones del formulario en deal-form.ts y la presentación
 *  en AmazonAutofillPanel / DealFormPanel / AdminDealsTable /
 *  DuplicateDealDialog. Aquí queda solo el flujo: autofill → form →
 *  guardar (con conflicto 409) → Telegram.
 */
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  dealsService,
  isDuplicateDealError,
  type DealDetailData,
  type DealCreatePayload,
  type DealUpdatePayload,
} from "@/services/api/deals";
import { productsApi, type AmazonPreviewResponse } from "@/services/api/products";
import { calculateDiscount, toDatetimeLocal } from "@/lib/format";
import { errorMessage } from "@/lib/errors";
import { DEAL_STATUS_OPTIONS } from "@/lib/constants";
import { dealFormSchema } from "@/lib/validation/deals";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/hooks/useAuth";
import {
  TelegramPanel,
  type TelegramScheduleRequest,
} from "@/features/telegram/components/TelegramPanel";
import type { TelegramGenerateRequest } from "@/services/api/telegram";
import {
  buildDealPayload,
  dealToForm,
  emptyForm,
  resolveCategorySelection,
  type DealForm,
} from "@/features/admin/deal-form";
import { useAdminDeals } from "@/features/admin/hooks/useAdminDeals";
import { useDealImages } from "@/features/admin/hooks/useDealImages";
import { AmazonAutofillPanel } from "@/features/admin/components/AmazonAutofillPanel";
import { DealFormPanel } from "@/features/admin/components/DealFormPanel";
import { AdminDealsTable } from "@/features/admin/components/AdminDealsTable";
import { DuplicateDealDialog } from "@/features/admin/components/DuplicateDealDialog";
import { ScheduledDealsCalendar } from "@/features/admin/components/ScheduledDealsCalendar";
import {
  scheduledDealsService,
  type ScheduledDealCreatePayload,
} from "@/services/api/scheduled-deals";
import { ApiError } from "@/services/api/client";

export const Route = createFileRoute("/admin/chollos")({
  validateSearch: (search: Record<string, unknown>) => ({
    edit: typeof search.edit === "string" ? search.edit : undefined,
  }),
  component: AdminDeals,
});

type TelegramPanelData = TelegramGenerateRequest & {
  images?: string[];
  image_url?: string | null;
};

function AdminDeals() {
  const { user } = useAuth();
  const { deals, statusFilter, setStatusFilter, stores, cats, subcats, load, remove } =
    useAdminDeals();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<DealDetailData | null>(null);
  const [form, setForm] = useState<DealForm>(emptyForm);
  const [amazonUrl, setAmazonUrl] = useState("");
  const [autofilling, setAutofilling] = useState(false);
  const [showTelegramPanel, setShowTelegramPanel] = useState(false);
  const [telegramDealData, setTelegramDealData] = useState<TelegramPanelData | null>(null);
  const [telegramCanSchedule, setTelegramCanSchedule] = useState(false);
  const [defaultScheduledAt, setDefaultScheduledAt] = useState<string | null>(null);
  const [calendarRefresh, setCalendarRefresh] = useState(0);
  const [calendarDealId, setCalendarDealId] = useState<string | null>(null);
  const images = useDealImages(form, setForm, user?.id);
  const nav = useNavigate();

  /** Diálogo de conflicto cuando el backend devuelve 409 DUPLICATE_DEAL.
   *  Guardamos también el payload original para poder reintentar como
   *  UPDATE sobre el deal existente si el admin elige "Sobrescribir". */
  const [duplicateConflict, setDuplicateConflict] = useState<{
    existing_deal: { id: string; slug: string; title: string };
    pendingPayload: DealCreatePayload;
  } | null>(null);

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
    if (d.status === "scheduled") {
      setShowForm(false);
      setCalendarDealId(d.id);
      return;
    }
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
      const categorySelection = resolveCategorySelection(
        d.category_id ?? "",
        d.subcategory_id ?? "",
        cats,
        subcats,
      );

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
        category_id: categorySelection?.category_id ?? d.category_id ?? "",
        subcategory_id: categorySelection?.subcategory_id ?? d.subcategory_id ?? "",
        expires_at: d.expires_at ? toDatetimeLocal(d.expires_at) : "",
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
      await openTelegramPanelWith(
        {
          title: d.title || "",
          current_price: d.current_price || 0,
          previous_price: d.original_price || null,
          discount_percentage: d.discount_percentage || null,
          description: d.telegram_text || d.short_description || null,
          affiliate_url: url,
          expires_at: d.expires_at,
          images: allImages,
          image_url: allImages[0] ?? null,
        },
        true,
      );
    } catch (e: unknown) {
      toast.error("Error desde el NAS: " + errorMessage(e));
    } finally {
      setAutofilling(false);
    }
  };

  /** Abre el panel Telegram con datos ya normalizados. */
  const openTelegramPanelWith = async (data: TelegramPanelData, canSchedule = false) => {
    let nextScheduledAt: string | null = null;
    if (canSchedule) {
      try {
        nextScheduledAt = (await scheduledDealsService.getNextSlot()).scheduled_at;
      } catch (error) {
        toast.error(errorMessage(error, "No se pudo calcular la siguiente hora disponible"));
      }
    }
    setTelegramDealData(data);
    setTelegramCanSchedule(canSchedule);
    setDefaultScheduledAt(nextScheduledAt);
    setShowTelegramPanel(true);
  };

  /** Abre el panel a partir del formulario actual. */
  const openTelegramPanelFromForm = async () => {
    const allImages = form.images.filter(Boolean);
    if (form.image_url && !allImages.includes(form.image_url)) allImages.unshift(form.image_url);
    const current = parseFloat(form.current_price) || 0;
    const previous = form.previous_price ? parseFloat(form.previous_price) : null;
    await openTelegramPanelWith(
      {
        title: form.title,
        current_price: current,
        previous_price: previous,
        discount_percentage: calculateDiscount(current, previous),
        description: form.telegram_text || form.short_description || null,
        affiliate_url: form.affiliate_url,
        expires_at: form.expires_at ? new Date(form.expires_at).toISOString() : null,
        images: allImages,
        image_url: allImages[0] ?? null,
      },
      !editing,
    );
  };

  /** Abre el panel a partir de un deal ya guardado. */
  const openTelegramPanelFromDeal = (d: DealDetailData) => {
    const allImages = (d.images ?? []).filter(Boolean);
    if (d.image_url && !allImages.includes(d.image_url)) allImages.unshift(d.image_url);
    void openTelegramPanelWith({
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

  const scheduleFromTelegram = async (request: TelegramScheduleRequest): Promise<boolean> => {
    if (!user) return false;

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
      return false;
    }
    const categorySelection = resolveCategorySelection(
      form.category_id,
      form.subcategory_id,
      cats,
      subcats,
    );
    if (!categorySelection) {
      toast.error("No se encontró la categoría y subcategoría Varios");
      return false;
    }
    const asin = form.external_id.trim().toUpperCase();
    if (!/^[A-Z0-9]{10}$/.test(asin)) {
      toast.error("Para programar se necesita un ASIN de Amazon válido (10 caracteres)");
      return false;
    }

    const selectedImages = form.images.filter(Boolean);
    if (request.image_url) {
      const existingIndex = selectedImages.indexOf(request.image_url);
      if (existingIndex >= 0) selectedImages.splice(existingIndex, 1);
      selectedImages.unshift(request.image_url);
    }
    const scheduledForm: DealForm = {
      ...form,
      ...categorySelection,
      status: "scheduled",
      scheduled_for: toDatetimeLocal(request.scheduled_at),
      telegram_text: request.text,
      image_url: request.image_url ?? form.image_url,
      images: selectedImages,
    };
    const payload = buildDealPayload(scheduledForm, null);
    const storeName = stores.find((store) => store.id === form.store_id)?.name ?? "Amazon";
    const scheduledPayload: ScheduledDealCreatePayload = {
      asin,
      title: payload.title,
      slug: payload.slug,
      description_web: payload.description ?? "",
      short_description: payload.short_description,
      telegram_text: request.text,
      telegram_channel_id: request.telegram_channel_id,
      offer_price: payload.current_price,
      regular_price: payload.previous_price,
      discount_percentage: payload.discount_percentage ?? 0,
      image_url: payload.image_url,
      images: payload.images,
      affiliate_url: payload.affiliate_url,
      store_name: storeName,
      store_id: payload.store_id,
      category_id: categorySelection.category_id,
      subcategory_id: payload.subcategory_id,
      brand: payload.brand,
      shipping_info: payload.shipping_info,
      expires_at: payload.expires_at,
      scheduled_at: request.scheduled_at,
      source: "manual",
      show_keepa_chart: payload.show_keepa_chart,
    };

    try {
      await scheduledDealsService.create(scheduledPayload);
      setForm(scheduledForm);
      setShowForm(false);
      setCalendarRefresh((value) => value + 1);
      load();
      toast.success("Telegram y web programados correctamente");
      return true;
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        toast.error("No se puede programar: falta actualizar o reiniciar la API");
        return false;
      }
      toast.error(errorMessage(error));
      return false;
    }
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
    const categorySelection = resolveCategorySelection(
      form.category_id,
      form.subcategory_id,
      cats,
      subcats,
    );
    if (!categorySelection) {
      toast.error("No se encontró la categoría y subcategoría Varios");
      return;
    }

    const formToSave = { ...form, ...categorySelection };
    const payload = buildDealPayload(formToSave, editing);
    try {
      if (!editing && form.status === "scheduled") {
        if (!form.scheduled_for) {
          toast.error("Indica la fecha y hora de publicación");
          return;
        }
        const asin = form.external_id.trim().toUpperCase();
        if (!/^[A-Z0-9]{10}$/.test(asin)) {
          toast.error("Para programar se necesita un ASIN de Amazon válido (10 caracteres)");
          return;
        }
        const storeName = stores.find((store) => store.id === form.store_id)?.name ?? "Amazon";
        const scheduledPayload: ScheduledDealCreatePayload = {
          asin,
          title: payload.title,
          slug: payload.slug,
          description_web: payload.description ?? "",
          short_description: payload.short_description,
          telegram_text: form.telegram_text ?? "",
          offer_price: payload.current_price,
          regular_price: payload.previous_price,
          discount_percentage: payload.discount_percentage ?? 0,
          image_url: payload.image_url,
          images: payload.images,
          affiliate_url: payload.affiliate_url,
          store_name: storeName,
          store_id: payload.store_id,
          category_id: categorySelection.category_id,
          subcategory_id: payload.subcategory_id,
          brand: payload.brand,
          shipping_info: payload.shipping_info,
          expires_at: payload.expires_at,
          scheduled_at: new Date(form.scheduled_for).toISOString(),
          source: "manual",
          show_keepa_chart: payload.show_keepa_chart,
        };
        await scheduledDealsService.create(scheduledPayload);
        toast.success("Chollo programado");
        setCalendarRefresh((value) => value + 1);
      } else if (editing) {
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

  return (
    <div>
      {showTelegramPanel && telegramDealData && (
        <TelegramPanel
          dealData={telegramDealData}
          onClose={() => setShowTelegramPanel(false)}
          onSchedule={telegramCanSchedule ? scheduleFromTelegram : undefined}
          defaultScheduledAt={defaultScheduledAt}
        />
      )}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <h2 className="font-mono text-sm uppercase text-cyan-glow">Gestión de chollos</h2>
        <div className="flex items-center gap-2">
          <select
            aria-label="Filtrar por estado"
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
            onClick={startNew}
            className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2 flex items-center gap-2 hover:bg-foreground"
          >
            <Plus className="size-4" /> NUEVO
          </button>
        </div>
      </div>

      <AmazonAutofillPanel
        url={amazonUrl}
        busy={autofilling}
        onUrlChange={setAmazonUrl}
        onAutofill={autofillFromAmazon}
      />

      <ScheduledDealsCalendar
        refreshToken={calendarRefresh}
        openDealId={calendarDealId}
        onOpenHandled={() => setCalendarDealId(null)}
        onChanged={() => {
          load();
          setCalendarRefresh((value) => value + 1);
        }}
      />

      {showForm && (
        <DealFormPanel
          form={form}
          setForm={setForm}
          isEditing={!!editing}
          stores={stores}
          cats={cats}
          subcats={subcats}
          images={images}
          onSubmit={save}
          onCancel={() => setShowForm(false)}
          onOpenTelegram={openTelegramPanelFromForm}
        />
      )}

      <AdminDealsTable
        deals={deals}
        onEdit={startEdit}
        onTelegram={openTelegramPanelFromDeal}
        onRemove={remove}
      />

      <DuplicateDealDialog
        open={!!duplicateConflict}
        existingTitle={duplicateConflict?.existing_deal.title}
        onClose={() => setDuplicateConflict(null)}
        onGoExisting={goEditExisting}
        onOverwrite={overwriteExisting}
      />
    </div>
  );
}
