import { beforeEach, describe, expect, it, vi } from "vitest";
import { loadBannerTops, resetBannerTopsCache } from "./bannerTops";
import { categoriesService } from "@/services/api/categories";
import { catalogService } from "@/services/api/catalog";
vi.mock("@/services/api/categories", () => ({ categoriesService: { getWithDeals: vi.fn() } }));
vi.mock("@/services/api/catalog", () => ({ catalogService: { top: vi.fn() } }));
const topOf = (title: string) =>
  [1, 2, 3].map((position) => ({
    id: `${title}-${position}`,
    title: `${title} ${position}`,
    position,
    image_url: null,
    vote_count: 1,
    current_price: null,
    deal_slug: null,
    deal_status: null,
  }));

beforeEach(() => {
  vi.clearAllMocks();
  resetBannerTopsCache();
});

describe("loadBannerTops", () => {
  it("preserves category rankings and survives an unavailable category", async () => {
    vi.mocked(categoriesService.getWithDeals).mockResolvedValue([
      { id: "a", slug: "audio", name: "Audio", parent_id: null, icon: null, display_order: 1 },
      { id: "b", slug: "pc", name: "PC", parent_id: null, icon: null, display_order: 2 },
    ]);
    vi.mocked(catalogService.top).mockImplementation(async (slug) => {
      if (slug === "pc") throw new Error("offline");
      return [1, 2, 3, 4].map((position) => ({
        id: String(position),
        title: `Audio ${position}`,
        position,
        image_url: null,
        vote_count: 5,
        current_price: null,
        deal_slug: null,
        deal_status: null,
      }));
    });
    const result = await loadBannerTops();
    expect(result).toHaveLength(1);
    expect(result[0]?.slug).toBe("audio");
    expect(result[0]?.products.map((p) => p.position)).toEqual([1, 2, 3]);
  });

  it("reutiliza el resultado en el navegador al cambiar de página o filtro", async () => {
    vi.mocked(categoriesService.getWithDeals).mockResolvedValue([
      { id: "a", slug: "audio", name: "Audio", parent_id: null, icon: null, display_order: 1 },
    ]);
    vi.mocked(catalogService.top).mockResolvedValue(topOf("Audio"));

    await loadBannerTops(1_000);
    await loadBannerTops(30_000);
    expect(categoriesService.getWithDeals).toHaveBeenCalledTimes(1);

    await loadBannerTops(62_000);
    expect(categoriesService.getWithDeals).toHaveBeenCalledTimes(2);
  });

  it("no cachea un fallo", async () => {
    vi.mocked(categoriesService.getWithDeals)
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValue([]);

    await expect(loadBannerTops(1_000)).rejects.toThrow("offline");
    await expect(loadBannerTops(2_000)).resolves.toEqual([]);
  });
});
