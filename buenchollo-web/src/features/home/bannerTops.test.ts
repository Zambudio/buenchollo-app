import { describe, expect, it, vi } from "vitest";
import { loadBannerTops } from "./bannerTops";
import { categoriesService } from "@/services/api/categories";
import { catalogService } from "@/services/api/catalog";
vi.mock("@/services/api/categories", () => ({ categoriesService: { getWithDeals: vi.fn() } }));
vi.mock("@/services/api/catalog", () => ({ catalogService: { top: vi.fn() } }));
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
});
