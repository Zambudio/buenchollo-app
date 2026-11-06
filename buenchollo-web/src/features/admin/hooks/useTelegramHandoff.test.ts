import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { DealDetailData } from "@/services/api/deals";
import { telegramDataFromDeal, useTelegramHandoff } from "./useTelegramHandoff";

const mocks = vi.hoisted(() => ({ getNextSlot: vi.fn(), toastError: vi.fn() }));

vi.mock("@/services/api/scheduled-deals", () => ({
  scheduledDealsService: { getNextSlot: mocks.getNextSlot },
}));
vi.mock("sonner", () => ({ toast: { error: mocks.toastError } }));

const deal = {
  id: "d1",
  slug: "monitor",
  title: "Monitor",
  current_price: 100,
  previous_price: 150,
  discount_percentage: 33,
  short_description: "Corto",
  affiliate_url: "https://www.amazon.es/dp/B0ABCDEF12?tag=buenchollo-21",
  expires_at: "2026-11-20T10:00:00Z",
  image_url: "https://img.test/main.webp",
  images: ["https://img.test/a.webp", ""],
} as DealDetailData;

beforeEach(() => vi.clearAllMocks());

describe("telegramDataFromDeal", () => {
  it("normaliza los datos de un deal guardado (principal primero)", () => {
    expect(telegramDataFromDeal(deal)).toEqual({
      deal_id: "d1",
      title: "Monitor",
      current_price: 100,
      previous_price: 150,
      discount_percentage: 33,
      description: "Corto",
      affiliate_url: "https://www.amazon.es/dp/B0ABCDEF12?tag=buenchollo-21",
      expires_at: "2026-11-20T10:00:00Z",
      images: ["https://img.test/main.webp", "https://img.test/a.webp"],
      image_url: "https://img.test/main.webp",
    });
  });

  it("sin descripción corta ni enlace usa null y cadena vacía", () => {
    const data = telegramDataFromDeal({
      ...deal,
      short_description: null,
      affiliate_url: null,
      image_url: null,
      images: [],
    });
    expect(data.description).toBeNull();
    expect(data.affiliate_url).toBe("");
    expect(data.images).toEqual([]);
    expect(data.image_url).toBeNull();
  });
});

describe("useTelegramHandoff", () => {
  it("arranca cerrado", () => {
    const { result } = renderHook(() => useTelegramHandoff());
    expect(result.current.open).toBe(false);
    expect(result.current.data).toBeNull();
  });

  it("openFromDeal abre sin programación ni consulta de franja", async () => {
    const { result } = renderHook(() => useTelegramHandoff());
    await act(async () => {
      result.current.openFromDeal(deal);
    });
    expect(result.current.open).toBe(true);
    expect(result.current.canSchedule).toBe(false);
    expect(result.current.defaultScheduledAt).toBeNull();
    expect(result.current.data?.title).toBe("Monitor");
    expect(mocks.getNextSlot).not.toHaveBeenCalled();
  });

  it("openWith con programación consulta la siguiente franja", async () => {
    mocks.getNextSlot.mockResolvedValue({ scheduled_at: "2026-11-05T09:00:00Z" });
    const { result } = renderHook(() => useTelegramHandoff());
    await act(async () => {
      await result.current.openWith(telegramDataFromDeal(deal), true);
    });
    expect(result.current.canSchedule).toBe(true);
    expect(result.current.defaultScheduledAt).toBe("2026-11-05T09:00:00Z");
  });

  it("si falla la franja avisa pero abre igualmente", async () => {
    mocks.getNextSlot.mockRejectedValue(new Error("caído"));
    const { result } = renderHook(() => useTelegramHandoff());
    await act(async () => {
      await result.current.openWith(telegramDataFromDeal(deal), true);
    });
    expect(mocks.toastError).toHaveBeenCalledWith("caído");
    expect(result.current.open).toBe(true);
    expect(result.current.defaultScheduledAt).toBeNull();
  });

  it("close cierra el panel", async () => {
    const { result } = renderHook(() => useTelegramHandoff());
    await act(async () => {
      result.current.openFromDeal(deal);
    });
    act(() => result.current.close());
    expect(result.current.open).toBe(false);
  });
});
