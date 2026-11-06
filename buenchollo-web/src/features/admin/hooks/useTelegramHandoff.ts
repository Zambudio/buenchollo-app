/** Estado y apertura del panel de Telegram del admin, compartido por
 *  admin.chollos y admin.propuestas. */
import { useCallback, useState } from "react";
import { toast } from "sonner";
import { errorMessage } from "@/lib/errors";
import type { DealDetailData } from "@/services/api/deals";
import { scheduledDealsService } from "@/services/api/scheduled-deals";
import type { TelegramGenerateRequest } from "@/services/api/telegram";

export type TelegramPanelData = TelegramGenerateRequest & {
  images?: string[];
  image_url?: string | null;
  deal_id?: string | null;
};

/** Datos del panel a partir de un deal ya guardado. */
export function telegramDataFromDeal(d: DealDetailData): TelegramPanelData {
  const allImages = (d.images ?? []).filter(Boolean);
  if (d.image_url && !allImages.includes(d.image_url)) allImages.unshift(d.image_url);
  return {
    deal_id: d.id,
    title: d.title,
    current_price: d.current_price,
    previous_price: d.previous_price,
    discount_percentage: d.discount_percentage,
    description: d.short_description || null,
    affiliate_url: d.affiliate_url ?? "",
    expires_at: d.expires_at,
    images: allImages,
    image_url: allImages[0] ?? null,
  };
}

export function useTelegramHandoff() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<TelegramPanelData | null>(null);
  const [canSchedule, setCanSchedule] = useState(false);
  const [defaultScheduledAt, setDefaultScheduledAt] = useState<string | null>(null);

  /** Abre el panel Telegram con datos ya normalizados. */
  const openWith = useCallback(async (next: TelegramPanelData, schedulable = false) => {
    let nextScheduledAt: string | null = null;
    if (schedulable) {
      try {
        nextScheduledAt = (await scheduledDealsService.getNextSlot()).scheduled_at;
      } catch (error) {
        toast.error(errorMessage(error, "No se pudo calcular la siguiente hora disponible"));
      }
    }
    setData(next);
    setCanSchedule(schedulable);
    setDefaultScheduledAt(nextScheduledAt);
    setOpen(true);
  }, []);

  /** Abre el panel a partir de un deal ya guardado. */
  const openFromDeal = useCallback(
    (d: DealDetailData) => {
      void openWith(telegramDataFromDeal(d));
    },
    [openWith],
  );

  const close = useCallback(() => setOpen(false), []);

  return { open, data, canSchedule, defaultScheduledAt, openWith, openFromDeal, close };
}

export type TelegramHandoff = ReturnType<typeof useTelegramHandoff>;
