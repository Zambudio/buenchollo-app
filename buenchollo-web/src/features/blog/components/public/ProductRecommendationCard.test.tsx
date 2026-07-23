import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderWithProviders } from "@/test/utils";
import { ProductRecommendationCard } from "./ProductRecommendationCard";

const mocks = vi.hoisted(() => ({ trackClick: vi.fn().mockResolvedValue(1) }));

vi.mock("@/services/api/deals", () => ({
  dealsService: { trackClick: mocks.trackClick },
}));

beforeEach(() => mocks.trackClick.mockClear());

describe("ProductRecommendationCard", () => {
  it("renderiza un producto manual con rel sponsored y sin registrar click de chollo", async () => {
    renderWithProviders(
      <ProductRecommendationCard
        attrs={{
          mode: "manual",
          deal_id: null,
          name: "Cargador USB-C 65W",
          image_url: null,
          affiliate_url: "https://amazon.es/dp/X",
          note: "Rápido y compacto",
          button_text: "Ver oferta",
          badge: "Nuestra elección",
        }}
      />,
    );

    const link = screen.getByRole("link", { name: "Ver oferta" });
    expect(link).toHaveAttribute("href", "https://amazon.es/dp/X");
    expect(link).toHaveAttribute("rel", "sponsored nofollow noopener");
    expect(screen.getByText("Cargador USB-C 65W")).toBeInTheDocument();

    await userEvent.click(link);
    expect(mocks.trackClick).not.toHaveBeenCalled();
  });

  it("un producto manual no muestra precio (nunca inventa precios)", () => {
    renderWithProviders(
      <ProductRecommendationCard
        attrs={{
          mode: "manual",
          deal_id: null,
          name: "Producto manual",
          image_url: null,
          affiliate_url: "https://amazon.es/dp/X",
          note: null,
          button_text: null,
          badge: null,
        }}
      />,
    );
    expect(screen.queryByText(/€/)).not.toBeInTheDocument();
  });

  it("muestra la imagen a 80 px en móvil y 96 px desde pantallas pequeñas", () => {
    renderWithProviders(
      <ProductRecommendationCard
        attrs={{
          mode: "manual",
          deal_id: null,
          name: "Producto con imagen",
          image_url: "https://example.com/producto.webp",
          affiliate_url: "https://amazon.es/dp/X",
          note: null,
          button_text: null,
          badge: null,
        }}
      />,
    );

    expect(screen.getByRole("img", { name: "Producto con imagen" })).toHaveClass(
      "size-20",
      "sm:size-24",
    );
  });

  it("un chollo existente registra el click antes de abrir el enlace", async () => {
    renderWithProviders(
      <ProductRecommendationCard
        attrs={{
          mode: "deal",
          deal_id: "deal-1",
          name: null,
          image_url: null,
          affiliate_url: null,
          note: null,
          button_text: null,
          badge: null,
        }}
        deal={{
          id: "deal-1",
          title: "Auriculares X",
          slug: "auriculares-x",
          image_url: null,
          affiliate_url: "https://amazon.es/dp/Y",
          store_name: "Amazon",
          current_price: 19.99,
          previous_price: 29.99,
          discount_percentage: 33,
          is_active: true,
        }}
      />,
    );

    const link = screen.getByRole("link", { name: /Ver oferta/i });
    expect(link).toHaveAttribute("rel", "sponsored nofollow noopener");
    expect(screen.getByText("19.99 €")).toBeInTheDocument();

    await userEvent.click(link);
    expect(mocks.trackClick).toHaveBeenCalledWith("deal-1");
  });

  it("oculta el precio si el chollo ya no está activo", () => {
    renderWithProviders(
      <ProductRecommendationCard
        attrs={{
          mode: "deal",
          deal_id: "deal-2",
          name: null,
          image_url: null,
          affiliate_url: null,
          note: null,
          button_text: null,
          badge: null,
        }}
        deal={{
          id: "deal-2",
          title: "Chollo expirado",
          slug: "chollo-expirado",
          image_url: null,
          affiliate_url: "https://amazon.es/dp/Z",
          store_name: "Amazon",
          current_price: 9.99,
          previous_price: null,
          discount_percentage: null,
          is_active: false,
        }}
      />,
    );
    expect(screen.queryByText(/€/)).not.toBeInTheDocument();
    expect(screen.getByRole("link")).toBeInTheDocument();
  });
});
