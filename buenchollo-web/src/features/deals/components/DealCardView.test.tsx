import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DealCardView, type DealCardData } from "./DealCardView";
import { formatPrice } from "@/lib/format";

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}));

const deal: DealCardData = {
  id: "d1",
  title: "Gratis",
  slug: "gratis",
  image_url: null,
  current_price: 0,
  previous_price: null,
  discount_percentage: null,
  temperature: 0,
  published_at: "2026-11-01T00:00:00Z",
};

describe("DealCardView precio", () => {
  it("la tarjeta interactiva siempre usa formatPrice (también con 0)", () => {
    const { container } = render(<DealCardView deal={deal} temperature={0} />);
    expect(container.querySelector(".price-now")!.textContent).toBe(formatPrice(0));
  });

  it("la vista previa sin precio muestra el marcador", () => {
    const { container } = render(<DealCardView preview deal={deal} temperature={0} />);
    expect(container.querySelector(".price-now")).toHaveTextContent("— €");
  });
});
