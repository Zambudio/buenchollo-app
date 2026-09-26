import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import interactionPlugin from "@fullcalendar/interaction";
import multiMonthPlugin from "@fullcalendar/multimonth";
import esLocale from "@fullcalendar/core/locales/es";
import type {
  DatesSetArg,
  DayCellContentArg,
  DayHeaderContentArg,
  EventClickArg,
  EventDropArg,
  EventInput,
} from "@fullcalendar/core";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CalendarDays, Trash2, X } from "lucide-react";
import { toast } from "sonner";

import { calculateDiscount, toDatetimeLocal } from "@/lib/format";
import { errorMessage } from "@/lib/errors";
import {
  scheduledDealsService,
  type ScheduledDealData,
  type ScheduledDealStatus,
} from "@/services/api/scheduled-deals";
import { ApiError } from "@/services/api/client";
import { telegramApi, type TelegramChannel } from "@/services/api/telegram";
import type { Category } from "@/services/api/categories";
import type { Store } from "@/services/api/stores";
import { adminInputCls as inputCls } from "../deal-form";

const STATUS_COLORS: Record<ScheduledDealStatus, string> = {
  programado: "#22D3EE",
  publicado: "#FACC15",
  cancelado_precio: "#EF4444",
  cancelado_stock: "#EF4444",
  error: "#EF4444",
};

const STATUS_LABELS: Record<ScheduledDealStatus, string> = {
  programado: "Programado",
  publicado: "Publicado",
  cancelado_precio: "Cancelado por precio",
  cancelado_stock: "Cancelado por stock",
  error: "Error",
};

interface Props {
  readonly refreshToken: number;
  readonly onChanged: () => void;
  readonly stores: Store[];
  readonly cats: Category[];
  readonly subcats: Category[];
  readonly openDealId?: string | null;
  readonly onOpenHandled?: () => void;
}

interface EditorState {
  asin: string;
  title: string;
  description_web: string;
  short_description: string;
  telegram_text: string;
  telegram_channel_id: string;
  offer_price: string;
  regular_price: string;
  image_url: string;
  images: string;
  affiliate_url: string;
  store_id: string;
  category_id: string;
  subcategory_id: string;
  brand: string;
  shipping_info: string;
  expires_at: string;
  show_keepa_chart: boolean;
  scheduled_at: string;
}

function editorFromDeal(deal: ScheduledDealData): EditorState {
  return {
    asin: deal.asin,
    title: deal.title,
    description_web: deal.description_web,
    short_description: deal.short_description ?? "",
    telegram_text: deal.telegram_text,
    telegram_channel_id: deal.telegram_channel_id ?? "",
    offer_price: String(deal.offer_price),
    regular_price: deal.regular_price == null ? "" : String(deal.regular_price),
    image_url: deal.image_url ?? "",
    images: deal.images.join("\n"),
    affiliate_url: deal.affiliate_url,
    store_id: deal.store_id ?? "",
    category_id: deal.category_id,
    subcategory_id: deal.subcategory_id ?? "",
    brand: deal.brand ?? "",
    shipping_info: deal.shipping_info ?? "",
    expires_at: deal.expires_at ? toDatetimeLocal(deal.expires_at) : "",
    show_keepa_chart: deal.show_keepa_chart,
    scheduled_at: toDatetimeLocal(deal.scheduled_at),
  };
}

function localDayKey(date: Date): string {
  return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
}

export function ScheduledDealsCalendar({
  refreshToken,
  onChanged,
  stores,
  cats,
  subcats,
  openDealId,
  onOpenHandled,
}: Props) {
  const [deals, setDeals] = useState<ScheduledDealData[]>([]);
  const [channels, setChannels] = useState<TelegramChannel[]>([]);
  const rangeRef = useRef<{ start: string; end: string } | null>(null);
  const apiWarningShown = useRef(false);
  const [selected, setSelected] = useState<ScheduledDealData | null>(null);
  const [editor, setEditor] = useState<EditorState | null>(null);
  const [saving, setSaving] = useState(false);

  const filteredSubcats = useMemo(
    () => subcats.filter((subcategory) => subcategory.parent_id === editor?.category_id),
    [editor?.category_id, subcats],
  );

  const load = useCallback(async (activeRange?: { start: string; end: string }) => {
    const targetRange = activeRange ?? rangeRef.current;
    if (!targetRange) return;
    try {
      setDeals(await scheduledDealsService.list(targetRange.start, targetRange.end));
      apiWarningShown.current = false;
    } catch (error) {
      if (apiWarningShown.current) return;
      apiWarningShown.current = true;
      if (error instanceof ApiError && error.status === 404) {
        toast.error("Calendario no disponible: falta actualizar o reiniciar la API");
        return;
      }
      toast.error(errorMessage(error, "No se pudo cargar el calendario"));
    }
  }, []);

  useEffect(() => {
    if (refreshToken === 0) return;
    void load();
  }, [load, refreshToken]);

  useEffect(() => {
    void telegramApi
      .getChannels()
      .then(setChannels)
      .catch(() => toast.error("No se pudieron cargar los canales de Telegram"));
  }, []);

  useEffect(() => {
    if (!openDealId) return;
    let active = true;
    void scheduledDealsService
      .getByDealId(openDealId)
      .then((deal) => {
        if (!active) return;
        setSelected(deal);
        setEditor(editorFromDeal(deal));
      })
      .catch((error) => {
        if (active) toast.error(errorMessage(error, "No se pudo abrir la programación"));
      })
      .finally(() => {
        if (active) onOpenHandled?.();
      });
    return () => {
      active = false;
    };
  }, [onOpenHandled, openDealId]);

  const density = useMemo(() => {
    const counts = new Map<string, number>();
    for (const deal of deals) {
      const key = localDayKey(new Date(deal.scheduled_at));
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    return counts;
  }, [deals]);

  const events: EventInput[] = useMemo(
    () =>
      deals.map((deal) => ({
        id: deal.id,
        title: `${deal.title} · ${deal.offer_price.toFixed(2)} €`,
        start: deal.scheduled_at,
        backgroundColor: STATUS_COLORS[deal.status],
        borderColor: STATUS_COLORS[deal.status],
        textColor:
          deal.status === "programado" || deal.status === "publicado" ? "#07131a" : "#ffffff",
        editable: deal.status === "programado",
        extendedProps: { deal },
      })),
    [deals],
  );

  const handleDatesSet = (info: DatesSetArg) => {
    const next = { start: info.start.toISOString(), end: info.end.toISOString() };
    rangeRef.current = next;
    void load(next);
  };

  const handleDrop = async (info: EventDropArg) => {
    if (!info.event.start) {
      info.revert();
      return;
    }
    try {
      await scheduledDealsService.reschedule(info.event.id, info.event.start.toISOString());
      toast.success("Fecha de publicación actualizada");
      await load();
      onChanged();
    } catch (error) {
      info.revert();
      toast.error(errorMessage(error, "No se pudo reprogramar"));
    }
  };

  const handleClick = (info: EventClickArg) => {
    const deal = info.event.extendedProps.deal as ScheduledDealData;
    setSelected(deal);
    setEditor(editorFromDeal(deal));
  };

  const countBadge = (date: Date) => {
    const count = density.get(localDayKey(date)) ?? 0;
    return count > 0 ? (
      <span className="scheduled-density" aria-label={`${count} chollos programados`}>
        {count}
      </span>
    ) : null;
  };

  const dayCellContent = (arg: DayCellContentArg) => (
    <div className="scheduled-day-number">
      <span>{arg.dayNumberText}</span>
      {countBadge(arg.date)}
    </div>
  );

  const dayHeaderContent = (arg: DayHeaderContentArg) => (
    <div className="scheduled-day-header">
      <span>{arg.text}</span>
      {arg.view.type.startsWith("timeGrid") && countBadge(arg.date)}
    </div>
  );

  const closeModal = () => {
    setSelected(null);
    setEditor(null);
  };

  const save = async () => {
    if (!selected || !editor) return;
    const current = Number(editor.offer_price);
    const regular = editor.regular_price ? Number(editor.regular_price) : null;
    const scheduledAt = new Date(editor.scheduled_at);
    const expiresAt = editor.expires_at ? new Date(editor.expires_at) : null;
    const asin = editor.asin.trim().toUpperCase();
    if (!/^[A-Z0-9]{10}$/.test(asin)) {
      toast.error("El ASIN debe tener 10 letras o números");
      return;
    }
    if (!editor.category_id) {
      toast.error("Selecciona una categoría web");
      return;
    }
    if (Number.isNaN(scheduledAt.getTime()) || scheduledAt <= new Date()) {
      toast.error("La fecha programada debe estar en el futuro");
      return;
    }
    if (expiresAt && !Number.isNaN(expiresAt.getTime()) && scheduledAt >= expiresAt) {
      toast.error("La publicación debe programarse antes de que caduque el chollo");
      return;
    }
    const webImages = editor.images
      .split(/\r?\n/)
      .map((image) => image.trim())
      .filter(Boolean)
      .slice(0, 20);
    const selectedStore = stores.find((store) => store.id === editor.store_id);
    setSaving(true);
    try {
      await scheduledDealsService.update(selected.id, {
        asin,
        title: editor.title,
        description_web: editor.description_web,
        short_description: editor.short_description || null,
        telegram_text: editor.telegram_text,
        telegram_channel_id: editor.telegram_channel_id || null,
        offer_price: current,
        regular_price: regular,
        discount_percentage: calculateDiscount(current, regular) ?? 0,
        image_url: editor.image_url || null,
        images: webImages,
        affiliate_url: editor.affiliate_url,
        store_id: editor.store_id || null,
        store_name: selectedStore?.name ?? selected.store_name,
        category_id: editor.category_id,
        subcategory_id: editor.subcategory_id || null,
        brand: editor.brand || null,
        shipping_info: editor.shipping_info || null,
        expires_at: expiresAt?.toISOString() ?? null,
        show_keepa_chart: editor.show_keepa_chart,
        scheduled_at: scheduledAt.toISOString(),
      });
      closeModal();
      toast.success("Programación actualizada");
      await load();
      onChanged();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!selected || !confirm("¿Borrar esta programación? El chollo quedará como borrador."))
      return;
    setSaving(true);
    try {
      await scheduledDealsService.delete(selected.id);
      closeModal();
      toast.success("Programación eliminada");
      await load();
      onChanged();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  const editable = selected?.status === "programado";

  return (
    <section className="scheduled-calendar bg-surface-800 border border-surface-700 p-3 sm:p-5 mb-6 overflow-hidden">
      <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
        <div className="flex items-center gap-2">
          <CalendarDays className="size-4 text-cyan-glow" />
          <h3 className="font-mono text-xs uppercase text-cyan-glow">Planificación</h3>
        </div>
        <div className="flex flex-wrap gap-x-3 gap-y-1 font-mono text-[10px] uppercase">
          <span className="text-cyan-glow">● Programado</span>
          <span className="text-yellow-600 dark:text-yellow-400">● Publicado</span>
          <span className="text-alert-red">● Cancelado / error</span>
        </div>
      </div>

      <FullCalendar
        plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin, multiMonthPlugin]}
        locale={esLocale}
        initialView="timeGridWeek"
        headerToolbar={{
          left: "prev,next today",
          center: "title",
          right: "multiMonthYear,dayGridMonth,timeGridWeek,timeGridDay",
        }}
        buttonText={{ today: "Hoy", year: "Año", month: "Mes", week: "Semana", day: "Día" }}
        events={events}
        editable
        eventStartEditable
        eventDurationEditable={false}
        eventDrop={handleDrop}
        eventClick={handleClick}
        datesSet={handleDatesSet}
        dayCellContent={dayCellContent}
        dayHeaderContent={dayHeaderContent}
        dayMaxEvents={3}
        multiMonthMaxColumns={3}
        snapDuration="00:05:00"
        slotMinTime="08:00:00"
        slotMaxTime="24:00:00"
        nowIndicator
        height="auto"
      />

      {selected && editor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6">
          <button
            className="absolute inset-0 bg-black/70"
            onClick={closeModal}
            aria-label="Cerrar"
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="scheduled-deal-editor-title"
            className="relative w-full max-w-4xl max-h-[92vh] overflow-y-auto bg-surface-800 border border-surface-600 p-4 sm:p-6"
          >
            <div className="flex items-start justify-between gap-3 mb-4">
              <div>
                <span
                  className="font-mono text-[10px] uppercase"
                  style={{ color: STATUS_COLORS[selected.status] }}
                >
                  {STATUS_LABELS[selected.status]}
                </span>
                <h4 id="scheduled-deal-editor-title" className="font-mono text-sm mt-1">
                  Vista previa y edición
                </h4>
              </div>
              <button onClick={closeModal} className="p-1 hover:text-red-500" aria-label="Cerrar">
                <X className="size-4" />
              </button>
            </div>

            {selected.cancellation_reason && (
              <p className="mb-4 border border-red-500/40 bg-red-500/10 p-3 text-xs text-red-800 dark:text-red-300">
                {selected.cancellation_reason}
              </p>
            )}

            <div className="grid sm:grid-cols-[180px_1fr] gap-4">
              <div className="bg-surface-900 border border-surface-700 aspect-square overflow-hidden">
                {editor.image_url ? (
                  <img src={editor.image_url} alt="" className="size-full object-contain" />
                ) : (
                  <div className="size-full grid place-items-center font-mono text-xs text-muted-foreground">
                    Sin imagen
                  </div>
                )}
              </div>
              <div className="space-y-3">
                <input
                  disabled={!editable}
                  value={editor.title}
                  onChange={(e) => setEditor({ ...editor, title: e.target.value })}
                  className={inputCls}
                  aria-label="Título web"
                />
                <input
                  disabled={!editable}
                  value={editor.short_description}
                  onChange={(e) => setEditor({ ...editor, short_description: e.target.value })}
                  className={inputCls}
                  aria-label="Resumen web"
                  placeholder="Descripción corta"
                />
                <div className="grid grid-cols-2 gap-3">
                  <input
                    disabled={!editable}
                    type="number"
                    step="0.01"
                    value={editor.offer_price}
                    onChange={(e) => setEditor({ ...editor, offer_price: e.target.value })}
                    className={inputCls}
                    aria-label="Precio oferta"
                  />
                  <input
                    disabled={!editable}
                    type="number"
                    step="0.01"
                    value={editor.regular_price}
                    onChange={(e) => setEditor({ ...editor, regular_price: e.target.value })}
                    className={inputCls}
                    aria-label="Precio habitual"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <input
                    disabled={!editable}
                    value={editor.brand}
                    onChange={(e) => setEditor({ ...editor, brand: e.target.value })}
                    className={inputCls}
                    aria-label="Marca web"
                    placeholder="Marca"
                  />
                  <input
                    disabled={!editable}
                    value={editor.shipping_info}
                    onChange={(e) => setEditor({ ...editor, shipping_info: e.target.value })}
                    className={inputCls}
                    aria-label="Envío web"
                    placeholder="Información de envío"
                  />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <select
                    disabled={!editable}
                    value={editor.store_id}
                    onChange={(e) => setEditor({ ...editor, store_id: e.target.value })}
                    className={inputCls}
                    aria-label="Tienda web"
                  >
                    <option value="">— Tienda —</option>
                    {stores.map((store) => (
                      <option key={store.id} value={store.id}>
                        {store.name}
                      </option>
                    ))}
                  </select>
                  <select
                    disabled={!editable}
                    required
                    value={editor.category_id}
                    onChange={(e) =>
                      setEditor({ ...editor, category_id: e.target.value, subcategory_id: "" })
                    }
                    className={inputCls}
                    aria-label="Categoría web"
                  >
                    <option value="">— Categoría —</option>
                    {cats.map((category) => (
                      <option key={category.id} value={category.id}>
                        {category.name}
                      </option>
                    ))}
                  </select>
                  <select
                    disabled={!editable || !editor.category_id || filteredSubcats.length === 0}
                    value={editor.subcategory_id}
                    onChange={(e) => setEditor({ ...editor, subcategory_id: e.target.value })}
                    className={inputCls}
                    aria-label="Subcategoría web"
                  >
                    <option value="">
                      {editor.category_id
                        ? filteredSubcats.length
                          ? "— Subcategoría —"
                          : "Sin subcategorías"
                        : "Elige categoría primero"}
                    </option>
                    {filteredSubcats.map((subcategory) => (
                      <option key={subcategory.id} value={subcategory.id}>
                        {subcategory.name}
                      </option>
                    ))}
                  </select>
                </div>
                <label className="block">
                  <span className="font-mono text-[10px] uppercase text-muted-foreground">
                    Canal destino
                  </span>
                  <select
                    disabled={!editable}
                    value={editor.telegram_channel_id}
                    onChange={(e) => setEditor({ ...editor, telegram_channel_id: e.target.value })}
                    className={inputCls + " mt-1"}
                  >
                    <option value="">Canal principal (programación anterior)</option>
                    {channels.map((channel) => (
                      <option key={channel.id} value={channel.id}>
                        {channel.name}
                      </option>
                    ))}
                  </select>
                </label>
                <input
                  disabled={!editable}
                  type="datetime-local"
                  step={300}
                  min={toDatetimeLocal(new Date().toISOString())}
                  max={selected.expires_at ? toDatetimeLocal(selected.expires_at) : undefined}
                  value={editor.scheduled_at}
                  onChange={(e) => setEditor({ ...editor, scheduled_at: e.target.value })}
                  className={inputCls}
                  aria-label="Fecha de publicación"
                />
                <input
                  disabled={!editable}
                  type="datetime-local"
                  value={editor.expires_at}
                  onChange={(e) => setEditor({ ...editor, expires_at: e.target.value })}
                  className={inputCls}
                  aria-label="Caducidad web"
                />
                <input
                  disabled={!editable}
                  value={editor.affiliate_url}
                  onChange={(e) => setEditor({ ...editor, affiliate_url: e.target.value })}
                  className={inputCls}
                  aria-label="URL afiliado"
                />
                <input
                  disabled={!editable}
                  value={editor.image_url}
                  onChange={(e) => setEditor({ ...editor, image_url: e.target.value })}
                  className={inputCls}
                  aria-label="URL imagen"
                />
                <div className="flex items-center gap-3 bg-surface-900 border border-surface-600 px-3 py-2.5">
                  <input
                    disabled={!editable}
                    value={editor.asin}
                    onChange={(e) => setEditor({ ...editor, asin: e.target.value })}
                    className="flex-1 bg-transparent font-mono text-xs outline-none"
                    aria-label="ASIN web"
                    placeholder="ASIN de Amazon"
                  />
                  <label className="flex items-center gap-2 font-mono text-[10px] text-muted-foreground whitespace-nowrap">
                    <input
                      disabled={!editable}
                      type="checkbox"
                      checked={editor.show_keepa_chart}
                      onChange={(e) => setEditor({ ...editor, show_keepa_chart: e.target.checked })}
                      className="accent-cyan-500"
                    />
                    Mostrar gráfica Keepa
                  </label>
                </div>
              </div>
            </div>

            <label className="block mt-4">
              <span className="font-mono text-[10px] uppercase text-muted-foreground">
                Imágenes web (una URL por línea)
              </span>
              <textarea
                disabled={!editable}
                rows={3}
                value={editor.images}
                onChange={(e) => setEditor({ ...editor, images: e.target.value })}
                className={inputCls + " mt-1"}
                aria-label="Imágenes web"
              />
            </label>

            <label className="block mt-4">
              <span className="font-mono text-[10px] uppercase text-muted-foreground">
                Descripción web
              </span>
              <textarea
                disabled={!editable}
                rows={3}
                value={editor.description_web}
                onChange={(e) => setEditor({ ...editor, description_web: e.target.value })}
                className={inputCls + " mt-1"}
              />
            </label>
            <label className="block mt-4">
              <span className="font-mono text-[10px] uppercase text-cyan-glow">
                Vista previa Telegram
              </span>
              <textarea
                disabled={!editable}
                rows={10}
                value={editor.telegram_text}
                onChange={(e) => setEditor({ ...editor, telegram_text: e.target.value })}
                className={inputCls + " mt-1 text-xs leading-relaxed"}
              />
            </label>

            {editable && (
              <div className="flex flex-col-reverse sm:flex-row sm:justify-between gap-2 mt-5">
                <button
                  disabled={saving}
                  onClick={remove}
                  className="border border-red-500/60 text-red-700 dark:text-red-400 px-4 py-2 font-mono text-xs flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  <Trash2 className="size-3.5" /> BORRAR PROGRAMACIÓN
                </button>
                <button
                  disabled={saving}
                  onClick={save}
                  className="bg-cyan-glow text-surface-900 px-5 py-2 font-mono text-xs font-bold disabled:opacity-50"
                >
                  {saving ? "GUARDANDO..." : "GUARDAR CAMBIOS"}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
